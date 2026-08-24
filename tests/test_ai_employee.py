from __future__ import annotations
import pytest
from bitnet_runtime.config import AppConfig
from bitnet_runtime.memory.db import DatabaseManager
from bitnet_runtime.inference.mock_engine import MockInferenceEngine
from verticals.ai_employee.approval import ApprovalGateManager, ApprovalStatus
from verticals.ai_employee.personas import EMPLOYEE_PERSONAS
from verticals.ai_employee.self_learning import SelfLearningEngine
from verticals.ai_employee.worker import AIEmployeeWorker

@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_employee.db"
    return DatabaseManager(db_file)

def test_all_eight_employee_personas_configured():
    assert len(EMPLOYEE_PERSONAS) == 8
    expected_keys = [
        "sales_alex", "support_elena", "marketing_marcus", "researcher_aris",
        "admin_clara", "recruiter_david", "finance_sophia", "developer_devin"
    ]
    for k in expected_keys:
        assert k in EMPLOYEE_PERSONAS
        p = EMPLOYEE_PERSONAS[k]
        assert len(p.name) > 0
        assert len(p.responsibilities) >= 3
        assert len(p.tools) >= 3
        assert len(p.kpis) >= 2
        assert len(p.allowed_actions) > 0
        assert len(p.approval_required_actions) > 0

def test_self_learning_engine_feedback_ingestion_and_retrieval(test_db):
    engine = SelfLearningEngine(test_db)
    emp_id = "sales_alex"

    # Ingest user feedback
    rule = engine.ingest_user_feedback(
        employee_id=emp_id,
        task="Draft sales proposal for Cyberdyne Systems",
        user_correction="Always format enterprise proposals with annual upfront billing discounts.",
    )

    assert rule.id.startswith("rule_")
    assert rule.employee_id == emp_id
    assert "annual upfront billing discounts" in rule.rule_text

    # Retrieve relevant learnings
    matched = engine.retrieve_relevant_learnings(emp_id, "Need proposal for new enterprise deal")
    assert len(matched) >= 1
    assert matched[0].id == rule.id
    assert matched[0].times_applied >= 1

    # Check prompt context formatting
    context = engine.format_prompt_context(emp_id, "proposal deal")
    assert "[Self-Learned Guidelines & Invariants]" in context
    assert "annual upfront billing discounts" in context

def test_approval_gate_lifecycle_and_feedback_learning(test_db):
    learning = SelfLearningEngine(test_db)
    gates = ApprovalGateManager(test_db, self_learning=learning)
    emp_id = "finance_sophia"

    # 1. Request approval for high-risk action
    req = gates.request_approval(
        employee_id=emp_id,
        action_name="post_ledger_entry",
        parameters={"amount": 45000, "vendor": "Acme Cloud", "account": "Hosting"},
        risk_level="high",
        reason="Expense exceeds $10k threshold",
    )
    assert req.id.startswith("appr_")
    assert req.status == ApprovalStatus.PENDING

    # 2. List pending
    pending = gates.list_requests(employee_id=emp_id, status=ApprovalStatus.PENDING)
    assert len(pending) == 1
    assert pending[0].id == req.id

    # 3. Resolve approval with operator feedback note
    resolved = gates.resolve_approval(
        request_id=req.id,
        approved=True,
        feedback_notes="Approved for Acme Cloud under master agreement #2026-B.",
    )
    assert resolved is not None
    assert resolved.status == ApprovalStatus.APPROVED
    assert resolved.resolved_at is not None

    # Verify self-learning loop automatically ingested the note
    rules = learning.list_learnings_for_employee(emp_id)
    assert len(rules) >= 1
    assert "master agreement #2026-B" in rules[0].rule_text

@pytest.mark.asyncio
async def test_ai_employee_worker_task_execution(test_db):
    cfg = AppConfig()
    cfg.memory.db_path = test_db.db_path
    inf = MockInferenceEngine()

    worker = AIEmployeeWorker(
        config=cfg,
        db=test_db,
        inference_engine=inf,
    )
    await worker.initialize()

    # Execute task with explicit feedback note
    res = await worker.execute_employee_task(
        employee_id="developer_devin",
        task_prompt="Refactor authentication handler",
        user_feedback="Always enforce timing-safe comparison on API token hashes.",
    )

    assert res["employee_name"] == "Devin Hayes"
    assert res["result"] is not None
    assert res["latency_ms"] >= 0

    # Next task for Devin should include the learned rule in context
    context = worker.self_learning.format_prompt_context("developer_devin", "API token authentication")
    assert "timing-safe comparison" in context
