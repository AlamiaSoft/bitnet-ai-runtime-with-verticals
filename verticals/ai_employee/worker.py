from __future__ import annotations
import uuid
from typing import Any, Dict, List, Optional
from bitnet_runtime.plugins.vertical_registry import VerticalManifest
from bitnet_runtime.logging import logger
from ..base_vertical import BaseVertical
from .crm_store import CRMStore, LeadRecord

class AIEmployeeWorker(BaseVertical):
    manifest = VerticalManifest(
        name="employee",
        title="AI Employee in a Box",
        description="SMB Autonomous Inbox, CRM & Briefings",
    )
    """
    Autonomous SMB AI Employee:
    - Ingests and triages incoming business inquiries
    - Automatically assigns priority, sentiment, and CRM tags
    - Drafts context-aware, personalized email responses
    - Compiles daily executive morning briefings
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.crm = CRMStore(self.db)

    async def initialize(self) -> None:
        logger.info(f"AI Employee worker initialized for: {self.config.verticals.ai_employee.business_name}")

    async def triage_inbound_lead(
        self,
        name: str,
        inquiry_text: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        company: Optional[str] = None,
    ) -> Dict[str, Any]:
        lead_id = f"lead_{uuid.uuid4().hex[:8]}"

        prompt = f"""Analyze this incoming customer inquiry for {self.config.verticals.ai_employee.business_name}:
Customer Name: {name}
Inquiry: {inquiry_text}

Provide:
1. Priority: [low | medium | high | urgent]
2. Sentiment: [positive | neutral | negative]
3. Draft Reply: [A professional, polite reply acknowledging their request]
"""
        resp = await self.inference_engine.complete(prompt)

        # Parse output
        priority = "high" if "high" in resp.text.lower() or "urgent" in resp.text.lower() else "medium"
        sentiment = "positive" if "positive" in resp.text.lower() else "neutral"

        lead = LeadRecord(
            id=lead_id,
            name=name,
            email=email,
            phone=phone,
            company=company,
            status="new",
            sentiment=sentiment,
            priority=priority,
            inquiry_text=inquiry_text,
            notes=f"AI Triaged: {resp.text[:150]}...",
        )
        self.crm.save_lead(lead)

        return {
            "lead_id": lead_id,
            "status": "triaged",
            "priority": priority,
            "sentiment": sentiment,
            "draft_reply": resp.text,
        }

    async def generate_morning_briefing(self) -> str:
        leads = self.crm.list_leads(status="new")
        summary_prompt = f"""You are the AI Executive Assistant for {self.config.verticals.ai_employee.business_name}.
Generate a crisp morning operational briefing for the management team.
Total New Leads: {len(leads)}
Leads List:
"""
        for l in leads[:5]:
            summary_prompt += f"- {l.name} ({l.company or 'Direct'}): {l.inquiry_text} [Priority: {l.priority}]\n"

        resp = await self.inference_engine.complete(summary_prompt)
        return resp.text
