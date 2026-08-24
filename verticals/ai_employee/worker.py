from __future__ import annotations
import time
import uuid
from typing import Any, Dict, List, Optional
from bitnet_runtime.logging import logger
from bitnet_runtime.model_garden.models import TaskType
from bitnet_runtime.plugins.vertical_registry import VerticalManifest
from ..base_vertical import BaseVertical
from .approval import ApprovalGateManager, PendingApproval
from .crm_store import CRMStore, LeadRecord
from .personas import EMPLOYEE_PERSONAS, EmployeePersona
from .self_learning import LearnedInsight, SelfLearningEngine

class AIEmployeeWorker(BaseVertical):
    manifest = VerticalManifest(
        name="employee",
        title="Alamia AI Digital Employees",
        description="Autonomous Self-Learning Digital Workforce with Multi-Tier AI Routing",
    )
    """
    Enterprise Self-Learning AI Employee Runtime:
    - 8 Standardized Role Personas (Sales, Support, Marketing, Research, Admin, Recruiter, Finance, Developer).
    - Dynamic Context Injection with Self-Learned Rules from past feedback.
    - Multi-Tier Model Dispatch via AI Router.
    - Human-in-the-loop Approval & Safety Gates.
    - CRM and Task Execution Engine.
    """

    def __init__(self, cfg=None, db=None, inference_engine=None, **kwargs):
        super().__init__(cfg=cfg)
        if db is not None:
            self.db = db
        if inference_engine is not None:
            self.inference_engine = inference_engine
        self.crm = CRMStore(self.db)
        self.self_learning = SelfLearningEngine(self.db)
        self.approval_gates = ApprovalGateManager(self.db, self_learning=self.self_learning)

    async def initialize(self) -> None:
        logger.info(f"AI Employee Platform initialized for: {self.config.verticals.ai_employee.business_name}")

    def get_persona(self, employee_id: str) -> EmployeePersona:
        return EMPLOYEE_PERSONAS.get(employee_id, EMPLOYEE_PERSONAS["sales_alex"])

    def list_personas(self) -> List[EmployeePersona]:
        return list(EMPLOYEE_PERSONAS.values())

    async def execute_employee_task(
        self,
        employee_id: str,
        task_prompt: str,
        user_feedback: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes a task as a specific employee with persistent persona context,
        self-learned rules, and multi-tier model routing.
        """
        persona = self.get_persona(employee_id)
        start_time = time.time()

        # 1. Ingest explicit feedback if provided
        if user_feedback:
            self.self_learning.ingest_user_feedback(
                employee_id=employee_id,
                task=task_prompt,
                user_correction=user_feedback,
                task_type=persona.primary_task_type.value,
            )

        # 2. Retrieve learned guidelines from episodic memory
        learned_context = self.self_learning.format_prompt_context(employee_id, task_prompt)

        # 3. Assemble full prompt
        full_system = f"""{persona.system_prompt}
{learned_context}"""
        composed_prompt = f"""{full_system}

Task:
{task_prompt}"""

        # 4. Route and execute
        resp = await self.inference_engine.complete(composed_prompt)
        latency_ms = round((time.time() - start_time) * 1000.0, 1)

        return {
            "employee_id": employee_id,
            "employee_name": persona.name,
            "role": persona.role,
            "task": task_prompt,
            "result": resp.text,
            "latency_ms": latency_ms,
            "learned_rules_applied": len(self.self_learning.retrieve_relevant_learnings(employee_id, task_prompt)),
        }

    async def triage_inbound_lead(
        self,
        name: str,
        inquiry_text: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        company: Optional[str] = None,
    ) -> Dict[str, Any]:
        lead_id = f"lead_{uuid.uuid4().hex[:8]}"
        persona = self.get_persona("sales_alex")
        learned_context = self.self_learning.format_prompt_context("sales_alex", inquiry_text)

        prompt = f"""{persona.system_prompt}
{learned_context}

Analyze this incoming customer inquiry for {self.config.verticals.ai_employee.business_name}:
Customer Name: {name}
Company: {company or 'Direct'}
Inquiry: {inquiry_text}

Provide:
1. Priority: [low | medium | high | urgent]
2. Sentiment: [positive | neutral | negative]
3. Deal Stage: [Qualification | Discovery | Proposal | Negotiation]
4. Draft Reply: [A personalized, consultative response]
"""
        resp = await self.inference_engine.complete(prompt)

        # Parse priority & sentiment
        text_lower = resp.text.lower()
        priority = "urgent" if "urgent" in text_lower else "high" if "high" in text_lower else "medium"
        sentiment = "positive" if "positive" in text_lower else "neutral"

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
            notes=f"Triaged by Alex Morgan: {resp.text[:150]}...",
        )
        self.crm.save_lead(lead)

        return {
            "lead_id": lead_id,
            "status": "triaged",
            "priority": priority,
            "sentiment": sentiment,
            "draft_reply": resp.text,
            "handled_by": persona.name,
        }

    async def generate_morning_briefing(self) -> str:
        persona = self.get_persona("admin_clara")
        leads = self.crm.list_leads(status="new")
        learned_context = self.self_learning.format_prompt_context("admin_clara", "morning briefing")

        summary_prompt = f"""{persona.system_prompt}
{learned_context}

Generate a crisp, executive morning briefing for {self.config.verticals.ai_employee.business_name}.
Total Inbound Leads: {len(leads)}
Active Leads:
"""
        for l in leads[:5]:
            summary_prompt += f"- {l.name} ({l.company or 'Direct'}): {l.inquiry_text} [Priority: {l.priority}]\n"

        resp = await self.inference_engine.complete(summary_prompt)
        return resp.text
