from __future__ import annotations
from bitnet_runtime.agent.scheduler import AgentScheduler
from bitnet_runtime.logging import logger
from .worker import AIEmployeeWorker

class EmployeeRoutineManager:
    """Manages automated recurring schedules for the AI Employee."""

    def __init__(self, worker: AIEmployeeWorker, scheduler: AgentScheduler):
        self.worker = worker
        self.scheduler = scheduler

    def register_routines(self) -> None:
        # Schedule morning briefing daily at 8:30 AM
        self.scheduler.add_cron_job(
            func=self.worker.generate_morning_briefing,
            cron_expression="30 8 * * *",
            job_id="ai_employee_morning_briefing",
        )
        logger.info("Registered AI Employee daily morning routine.")
