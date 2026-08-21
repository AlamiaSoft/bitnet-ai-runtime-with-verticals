from __future__ import annotations
from typing import Any, Dict
from fastapi import APIRouter
from pydantic import BaseModel
from ...logging import logger

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

class InboundMessage(BaseModel):
    sender_id: str
    message: str
    channel: str = "whatsapp"
    metadata: Dict[str, Any] = {}

@router.post("/whatsapp")
async def whatsapp_webhook(msg: InboundMessage):
    logger.info(f"Received WhatsApp webhook from {msg.sender_id}: {msg.message}")
    # In a full vertical deployment, this routes directly into the WhatsApp Vertical
    return {"status": "received", "sender_id": msg.sender_id}

@router.post("/leads")
async def leads_webhook(lead_data: Dict[str, Any]):
    logger.info(f"Received new inbound lead webhook: {lead_data}")
    return {"status": "received", "data": lead_data}
