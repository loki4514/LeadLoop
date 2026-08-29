"""Public (unauthenticated) endpoints backing the embeddable chat widget.

Customer chat is plain HTTP POST per turn, per the architecture spec. No auth:
the conversation id acts as the session handle. Keep responses free of any
internal data (scores, tiers, assignments are never returned here).
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.service import GREETING, run_agent_turn
from app.api.sse import message_stream
from app.core.ratelimit import limiter
from app.db.session import get_db
from app.models.conversation import Conversation
from app.models.lead import Lead
from app.schemas.widget import (
    WidgetMessageRequest,
    WidgetMessageResponse,
    WidgetSessionCreate,
    WidgetSessionRead,
)

router = APIRouter(prefix="/widget", tags=["widget"])


@router.post("/sessions", response_model=WidgetSessionRead)
@limiter.limit("10/minute")
async def create_session(
    request: Request,
    body: WidgetSessionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Start a widget chat: creates the lead (tagged with its ad source) and
    its web conversation, and returns the opening greeting.

    Rate-limited per IP: session creation makes unbounded Lead rows otherwise."""
    lead = Lead(ad_source=body.ad_source)
    db.add(lead)
    await db.flush()

    convo = Conversation(lead_id=lead.id, channel="web", title="Website chat")
    db.add(convo)
    await db.flush()
    await db.commit()

    return WidgetSessionRead(
        lead_id=lead.id, conversation_id=convo.id, greeting=GREETING
    )


@router.post("/messages", response_model=WidgetMessageResponse)
@limiter.limit("20/minute")
async def send_message(
    request: Request,
    body: WidgetMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    """One chat turn: persist the lead's message, run the qualifier agent, and
    return its reply.

    Rate-limited per IP: this calls the paid LLM, so it's the main cost-abuse
    surface."""
    reply = await run_agent_turn(db, body.conversation_id, body.message)
    return WidgetMessageResponse(reply=reply)


@router.get("/stream")
async def stream_widget_messages(
    conversation_id: int = Query(...),
    after: int = Query(0, description="Only stream messages with id > this"),
    db: AsyncSession = Depends(get_db),
):
    """Public SSE stream of new messages for a widget conversation.

    Lets the lead see employee (human-takeover) replies in real time without
    sending another message. No auth — the conversation id is the session
    handle, same as /messages. Scoped to that one web conversation.
    """
    convo = await db.get(Conversation, conversation_id)
    if convo is None or convo.channel != "web":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )
    return message_stream(conversation_id, after)
