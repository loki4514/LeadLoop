"""Shared Server-Sent Events helper for streaming conversation messages.

Both the employee dashboard (authenticated, lead-scoped) and the public widget
(unauthenticated, conversation-scoped) push new messages the same way: poll the
DB for rows newer than the last id sent, emit them as SSE, keep the connection
alive through idle proxies. The browser's EventSource reconnects on drop.
"""
import asyncio
import json
from collections.abc import AsyncIterator

from sqlalchemy import select
from starlette.responses import StreamingResponse

from app.db.session import AsyncSessionLocal
from app.models.message import Message

# How often to poll for new messages, and a keep-alive comment interval so idle
# connections aren't closed by proxies.
POLL_SECONDS = 2.0
KEEPALIVE_SECONDS = 15.0


async def _message_events(conversation_id: int, after_id: int) -> AsyncIterator[str]:
    last_id = after_id
    idle = 0.0
    # Dedicated session — this loop outlives the request-scoped db dependency.
    async with AsyncSessionLocal() as db:
        while True:
            rows = (
                await db.execute(
                    select(Message)
                    .where(
                        Message.conversation_id == conversation_id,
                        Message.id > last_id,
                    )
                    .order_by(Message.id)
                )
            ).scalars().all()
            if rows:
                for m in rows:
                    payload = json.dumps({
                        "id": m.id,
                        "sender": m.sender.value,
                        "body": m.body,
                        "created_at": m.created_at.isoformat(),
                    })
                    yield f"id: {m.id}\nevent: message\ndata: {payload}\n\n"
                    last_id = m.id
                idle = 0.0
            else:
                idle += POLL_SECONDS
                if idle >= KEEPALIVE_SECONDS:
                    yield ": keep-alive\n\n"
                    idle = 0.0
            # End the transaction so the next poll gets a fresh snapshot —
            # otherwise a long-lived session never sees rows committed by other
            # connections (the reply / agent turn) after its first read.
            await db.commit()
            await asyncio.sleep(POLL_SECONDS)


def message_stream(conversation_id: int, after_id: int) -> StreamingResponse:
    """SSE response streaming messages in a conversation newer than ``after_id``."""
    return StreamingResponse(
        _message_events(conversation_id, after_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering for SSE
        },
    )
