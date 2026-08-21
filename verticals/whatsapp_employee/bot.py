from __future__ import annotations
from typing import Any, Dict
from bitnet_runtime.logging import logger
from bitnet_runtime.plugins.vertical_registry import VerticalManifest
from ..base_vertical import BaseVertical
from .catalog import CatalogManager
from .order_manager import OrderManager

class WhatsAppBot(BaseVertical):
    manifest = VerticalManifest(
        name="whatsapp",
        title="AI WhatsApp Employee",
        description="Inbound Order, Booking & Chat Assistant",
    )
    """
    AI WhatsApp Employee:
    - Conversational food ordering / clinic appointment assistant
    - Automatic menu inquiry handling and order drafting
    - Works offline and via local webhooks
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.catalog = CatalogManager()
        self.order_manager = OrderManager()

    async def initialize(self) -> None:
        logger.info("WhatsApp Employee Bot initialized.")

    async def handle_message(self, sender_id: str, message: str) -> Dict[str, Any]:
        msg_lower = message.lower()

        # Direct menu check
        if "menu" in msg_lower or "list" in msg_lower:
            return {
                "reply": f"Here is our menu:\n\n{self.catalog.get_full_menu_text()}\n\nReply with the items you'd like to order and your address!",
                "action": "menu_sent",
            }

        # Order / Inquiry reasoning via InferenceEngine
        prompt = f"""You are the WhatsApp ordering assistant for a restaurant.
Customer Message: "{message}"
Available Menu:
{self.catalog.get_full_menu_text()}

Respond politely, confirm items, calculate approximate total, or ask for delivery address.
Reply:"""
        resp = await self.inference_engine.complete(prompt)

        return {
            "reply": resp.text.strip(),
            "action": "order_reply",
            "sender_id": sender_id,
        }
