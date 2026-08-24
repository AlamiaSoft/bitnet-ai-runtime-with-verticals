from __future__ import annotations
import enum
import json
import sqlite3
import time
import uuid
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional
from bitnet_runtime.logging import logger
from bitnet_runtime.memory.db import DatabaseManager
from .self_learning import SelfLearningEngine

class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"

@dataclass
class PendingApproval:
    id: str
    employee_id: str
    action_name: str
    parameters: Dict[str, Any]
    risk_level: str  # "medium", "high", "critical"
    reason: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    feedback_notes: Optional[str] = None
    created_at: float = 0.0
    resolved_at: Optional[float] = None

class ApprovalGateManager:
    """
    Human-in-the-loop Safety and Permission Gate for AI Employees:
    - Traps high-risk actions before execution.
    - Maintains an audit queue for operator approval.
    - Feeds approval outcomes and operator feedback directly into the Self-Learning Engine.
    """

    def __init__(self, db: DatabaseManager, self_learning: Optional[SelfLearningEngine] = None):
        self.db = db
        self.self_learning = self_learning or SelfLearningEngine(db)
        self._init_db()

    def _init_db(self) -> None:
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS approval_requests (
                id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                action_name TEXT NOT NULL,
                parameters TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL,
                feedback_notes TEXT,
                created_at REAL NOT NULL,
                resolved_at REAL
            )
        """)
        self.db.execute("CREATE INDEX IF NOT EXISTS idx_approval_status ON approval_requests(status)")

    def request_approval(
        self,
        employee_id: str,
        action_name: str,
        parameters: Dict[str, Any],
        risk_level: str = "high",
        reason: str = "Action requires human authorization",
    ) -> PendingApproval:
        req_id = f"appr_{uuid.uuid4().hex[:8]}"
        now = time.time()

        appr = PendingApproval(
            id=req_id,
            employee_id=employee_id,
            action_name=action_name,
            parameters=parameters,
            risk_level=risk_level,
            reason=reason,
            status=ApprovalStatus.PENDING,
            feedback_notes=None,
            created_at=now,
            resolved_at=None,
        )

        self.db.execute(
            """
            INSERT INTO approval_requests (
                id, employee_id, action_name, parameters, risk_level,
                reason, status, feedback_notes, created_at, resolved_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                appr.id,
                appr.employee_id,
                appr.action_name,
                json.dumps(appr.parameters),
                appr.risk_level,
                appr.reason,
                appr.status.value,
                appr.feedback_notes,
                appr.created_at,
                appr.resolved_at,
            ),
        )

        logger.info(f"Created pending approval request '{req_id}' for employee '{employee_id}' (action: {action_name})")
        return appr

    def list_requests(
        self,
        employee_id: Optional[str] = None,
        status: Optional[ApprovalStatus] = None,
    ) -> List[PendingApproval]:
        query = "SELECT id, employee_id, action_name, parameters, risk_level, reason, status, feedback_notes, created_at, resolved_at FROM approval_requests"
        params = []
        conditions = []

        if employee_id:
            conditions.append("employee_id = ?")
            params.append(employee_id)
        if status:
            conditions.append("status = ?")
            params.append(status.value if hasattr(status, "value") else str(status))

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY created_at DESC"

        rows = self.db.fetchall(query, tuple(params))

        return [
            PendingApproval(
                id=r[0],
                employee_id=r[1],
                action_name=r[2],
                parameters=json.loads(r[3]),
                risk_level=r[4],
                reason=r[5],
                status=ApprovalStatus(r[6]),
                feedback_notes=r[7],
                created_at=r[8],
                resolved_at=r[9],
            )
            for r in rows
        ]

    def resolve_approval(
        self,
        request_id: str,
        approved: bool,
        feedback_notes: Optional[str] = None,
    ) -> Optional[PendingApproval]:
        requests = self.list_requests()
        target = next((r for r in requests if r.id == request_id), None)
        if not target:
            return None

        new_status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        resolved_at = time.time()

        self.db.execute(
            "UPDATE approval_requests SET status = ?, feedback_notes = ?, resolved_at = ? WHERE id = ?",
            (new_status.value, feedback_notes, resolved_at, request_id),
        )

        target.status = new_status
        target.feedback_notes = feedback_notes
        target.resolved_at = resolved_at

        # Trigger self-learning loop if feedback notes were provided
        if feedback_notes and self.self_learning:
            self.self_learning.ingest_user_feedback(
                employee_id=target.employee_id,
                task=f"Action {target.action_name}: {json.dumps(target.parameters)}",
                user_correction=feedback_notes,
                task_type="approval_feedback",
            )

        logger.info(f"Resolved approval request '{request_id}' -> {new_status.value}")
        return target
