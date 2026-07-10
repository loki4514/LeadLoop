"""Public (unauthenticated) endpoints backing the embeddable chat widget.

Customer chat is plain HTTP POST per turn, per the architecture spec. No auth:
the conversation id acts as the session handle. Keep responses free of any
internal data (scores, tiers, assignments are never returned here).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import run_agent_turn
from app.agent.service import GREETING
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
async def create_session(
    body: WidgetSessionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Start a widget chat: creates the lead (tagged with its ad source) and
    its web conversation, and returns the opening greeting."""
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
async def send_message(
    body: WidgetMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    """One chat turn: persist the lead's message, run the qualifier agent, and
    return its reply."""
    reply = await run_agent_turn(db, body.conversation_id, body.message)
    return WidgetMessageResponse(reply=reply)
