from __future__ import annotations
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from .db import DatabaseManager

@dataclass
class InteractionEvent:
    session_id: str
    step_number: int
    event_type: str  # "user_prompt", "thought", "tool_call", "tool_output", "final_answer"
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: Optional[int] = None
    timestamp: Optional[str] = None

class EpisodicMemory:
    """
    Tracks multi-turn agent conversations, tool invocation transcripts,
    and step-by-step reasoning logs.
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def create_session(self, title: str = "Agent Session", metadata: Optional[Dict[str, Any]] = None) -> str:
        session_id = str(uuid.uuid4())
        with self.db.get_connection() as conn:
            conn.execute(
                "INSERT INTO agent_sessions (id, title, metadata) VALUES (?, ?, ?)",
                (session_id, title, json.dumps(metadata or {})),
            )
            conn.commit()
        return session_id

    def log_event(
        self,
        session_id: str,
        step_number: int,
        event_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO episodic_logs (session_id, step_number, event_type, content, metadata)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, step_number, event_type, content, json.dumps(metadata or {})),
            )
            conn.commit()

    def get_session_history(self, session_id: str, limit: int = 50) -> List[InteractionEvent]:
        rows = self.db.fetchall(
            """
            SELECT id, session_id, step_number, event_type, content, metadata, timestamp
            FROM episodic_logs
            WHERE session_id = ?
            ORDER BY step_number ASC, id ASC
            LIMIT ?
            """,
            (session_id, limit),
        )
        return [
            InteractionEvent(
                id=r["id"],
                session_id=r["session_id"],
                step_number=r["step_number"],
                event_type=r["event_type"],
                content=r["content"],
                metadata=json.loads(r["metadata"]) if r["metadata"] else {},
                timestamp=r["timestamp"],
            )
            for r in rows
        ]
