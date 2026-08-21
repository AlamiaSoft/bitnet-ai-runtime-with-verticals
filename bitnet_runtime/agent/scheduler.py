from __future__ import annotations
import asyncio
from typing import Any, Callable, Dict, List, Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from ..logging import logger

class AgentScheduler:
    """
    Background cron and interval scheduler for continuous local agent routines.
    """

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._is_running = False

    def start(self) -> None:
        if not self._is_running:
            self.scheduler.start()
            self._is_running = True
            logger.info("AgentScheduler started.")

    def shutdown(self) -> None:
        if self._is_running:
            self.scheduler.shutdown()
            self._is_running = False
            logger.info("AgentScheduler stopped.")

    def add_interval_job(
        self,
        func: Callable,
        seconds: int,
        job_id: str,
        args: Optional[List[Any]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.scheduler.add_job(
            func,
            "interval",
            seconds=seconds,
            id=job_id,
            args=args or [],
            kwargs=kwargs or {},
            replace_existing=True,
        )
        logger.info(f"Registered interval job '{job_id}' (every {seconds}s)")

    def add_cron_job(
        self,
        func: Callable,
        cron_expression: str,  # e.g. "0 9 * * *"
        job_id: str,
        args: Optional[List[Any]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        parts = cron_expression.split()
        if len(parts) == 5:
            minute, hour, day, month, day_of_week = parts
            self.scheduler.add_job(
                func,
                "cron",
                minute=minute,
                hour=hour,
                day=day,
                month=month,
                day_of_week=day_of_week,
                id=job_id,
                args=args or [],
                kwargs=kwargs or {},
                replace_existing=True,
            )
            logger.info(f"Registered cron job '{job_id}' ({cron_expression})")
