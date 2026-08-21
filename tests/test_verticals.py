import pytest
from bitnet_runtime.config import AppConfig
from verticals.ai_employee.worker import AIEmployeeWorker
from verticals.personal_memory.memory_os import PersonalMemoryOS
from verticals.ai_computer.computer_agent import AIComputerAgent
from verticals.whatsapp_employee.bot import WhatsAppBot
from verticals.qa_box.qa_runner import QABoxRunner

@pytest.fixture
def custom_config(tmp_path):
    cfg = AppConfig()
    cfg.memory.db_path = tmp_path / "test_verticals.db"
    cfg.agent.working_dir = tmp_path / "workspace"
    cfg.inference.default_provider = "mock"
    return cfg

@pytest.mark.asyncio
async def test_ai_employee_vertical(custom_config):
    worker = AIEmployeeWorker(cfg=custom_config)
    await worker.initialize()

    res = await worker.triage_inbound_lead(
        name="Tariq Khan",
        inquiry_text="Need an office lease for 50 people in Karachi",
        email="tariq@example.com",
    )
    assert res["status"] == "triaged"
    assert res["lead_id"].startswith("lead_")

    leads = worker.crm.list_leads()
    assert len(leads) == 1
    assert leads[0].name == "Tariq Khan"

    briefing = await worker.generate_morning_briefing()
    assert len(briefing) > 0

@pytest.mark.asyncio
async def test_personal_memory_vertical(custom_config, tmp_path):
    doc_dir = tmp_path / "docs"
    doc_dir.mkdir()
    (doc_dir / "note.txt").write_text("Meeting with Ahmed: decided on $50k seed investment.", encoding="utf-8")

    custom_config.verticals.personal_memory.watch_directories = [str(doc_dir)]
    mem_os = PersonalMemoryOS(cfg=custom_config)
    await mem_os.initialize()

    ans = await mem_os.ask("What was agreed with Ahmed?")
    assert "answer" in ans
    assert len(ans["citations"]) > 0

@pytest.mark.asyncio
async def test_ai_computer_vertical(custom_config):
    agent = AIComputerAgent(cfg=custom_config)
    await agent.initialize()

    audit = await agent.inspect_and_audit()
    assert "structure" in audit
    assert "recommendations" in audit

@pytest.mark.asyncio
async def test_whatsapp_bot_vertical(custom_config):
    bot = WhatsAppBot(cfg=custom_config)
    await bot.initialize()

    # Menu query
    menu_res = await bot.handle_message("923001234567", "Can I see the menu?")
    assert menu_res["action"] == "menu_sent"
    assert "Zinger Burger" in menu_res["reply"]

    # Order query
    order_res = await bot.handle_message("923001234567", "I want 2 burgers delivered to DHA")
    assert order_res["action"] == "order_reply"

@pytest.mark.asyncio
async def test_qa_box_vertical(custom_config):
    qa = QABoxRunner(cfg=custom_config)
    await qa.initialize()

    # Check local mock URLs
    report = await qa.run_endpoint_checks(["http://localhost:8000/health"])
    assert "report_markdown" in report
    assert len(report["results"]) == 1
