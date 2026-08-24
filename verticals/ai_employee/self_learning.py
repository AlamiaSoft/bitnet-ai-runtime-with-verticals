from __future__ import annotations
import json
import sqlite3
import time
import uuid
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional
from bitnet_runtime.logging import logger
from bitnet_runtime.memory.db import DatabaseManager

@dataclass
class LearnedInsight:
    id: str
    employee_id: str
    task_type: str
    trigger_pattern: str
    rule_type: str  # "preference", "constraint", "heuristic", "correction"
    rule_text: str
    source_feedback: Optional[str] = None
    confidence: float = 1.0
    created_at: float = 0.0
    times_applied: int = 0

class SelfLearningEngine:
    """
    Episodic Self-Learning Engine for AI Employees:
    - Extracts structured invariants, rules, and few-shot guidance from task outcomes and user corrections.
    - Persists insights into an indexed knowledge store.
    - Dynamically retrieves and injects active learned rules into working context before task execution.
    - Calibrates employee behavior over time without touching model weights.
    """

    def __init__(self, db: DatabaseManager):
        self.db = db
        self._init_db()

    def _init_db(self) -> None:
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS learned_rules (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                task_type TEXT NOT NULL,
                trigger_pattern TEXT NOT NULL,
                rule_type TEXT NOT NULL,
                rule_text TEXT NOT NULL,
                source_feedback TEXT,
                confidence REAL DEFAULT 1.0,
                created_at REAL NOT NULL,
                times_applied INTEGER DEFAULT 0
            )
        """)
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_rules_emp ON learned_rules(employee_id)")

    def ingest_user_feedback(
        self,
        employee_id: str,
        task: str,
        user_correction: str,
        task_type: str = "general",
    ) -> LearnedInsight:
        """Transforms explicit user feedback/correction into a persistent learned rule."""
        rule_id = f"rule_{uuid.uuid4().hex[:8]}"
        now = time.time()

        # Clean and extract the rule text
        rule_text = user_correction.strip()
        if not rule_text.endswith("."):
            rule_text += "."

        insight = LearnedInsight(
            id=rule_id,
            employee_id=employee_id,
            task_type=task_type,
            trigger_pattern=task[:100],
            rule_type="correction",
            rule_text=rule_text,
            source_feedback=user_correction,
            confidence=1.0,
            created_at=now,
            times_applied=0,
        )

        self.db.execute(
            """
            INSERT INTO learned_rules (
                id, employee_id, task_type, trigger_pattern, rule_type,
                rule_text, source_feedback, confidence, created_at, times_applied
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                insight.id,
                insight.employee_id,
                insight.task_type,
                insight.trigger_pattern,
                insight.rule_type,
                insight.rule_text,
                insight.source_feedback,
                insight.confidence,
                insight.created_at,
                insight.times_applied,
            ),
        )

        logger.info(f"AI Employee '{employee_id}' learned new rule: '{rule_text}'")
        return insight

    def list_learnings_for_employee(self, employee_id: str) -> List[LearnedInsight]:
        """Lists all active learned rules and guidelines for a given employee."""
        rows = self.db.fetchall(
            "SELECT id, employee_id, task_type, trigger_pattern, rule_type, rule_text, source_feedback, confidence, created_at, times_applied FROM learned_rules WHERE employee_id = ? ORDER BY created_at DESC",
            (employee_id,),
        )

        return [
            LearnedInsight(
                id=r[0],
                employee_id=r[1],
                task_type=r[2],
                trigger_pattern=r[3],
                rule_type=r[4],
                rule_text=r[5],
                source_feedback=r[6],
                confidence=r[7],
                created_at=r[8],
                times_applied=r[9],
            )
            for r in rows
        ]

    def retrieve_relevant_learnings(
        self,
        employee_id: str,
        query: str,
        limit: int = 3,
    ) -> List[LearnedInsight]:
        """Retrieves matching learned rules for the current task context."""
        rules = self.list_learnings_for_employee(employee_id)
        if not rules:
            return []

        # Keyword matching & recency scoring
        query_words = set(query.lower().split())
        scored: List[tuple[float, LearnedInsight]] = []

        for r in rules:
            overlap = sum(1 for w in query_words if w in r.trigger_pattern.lower() or w in r.rule_text.lower())
            recency = r.created_at / 1e10
            score = (overlap * 2.0) + (r.confidence * 1.5) + recency
            scored.append((score, r))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = [item[1] for item in scored[:limit]]

        # Increment times_applied
        for item in top:
            item.times_applied += 1
            self.db.execute("UPDATE learned_rules SET times_applied = times_applied + 1 WHERE id = ?", (item.id,))

        return top

    def format_prompt_context(self, employee_id: str, query: str) -> str:
        """Formats relevant learned insights as high-priority behavioral guidelines in prompts."""
        learnings = self.retrieve_relevant_learnings(employee_id, query, limit=4)
        if not learnings:
            return ""

        guidelines = "\n".join(f"- [Learned Guideline]: {l.rule_text}" for l in learnings)
        return f"""
[Self-Learned Guidelines & Invariants]:
{guidelines}
"""
