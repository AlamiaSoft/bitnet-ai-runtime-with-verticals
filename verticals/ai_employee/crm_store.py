from __future__ import annotations
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from bitnet_runtime.memory.db import DatabaseManager

CRM_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS crm_leads (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    company TEXT,
    status TEXT DEFAULT 'new',
    sentiment TEXT,
    priority TEXT DEFAULT 'medium',
    inquiry_text TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

@dataclass
class LeadRecord:
    id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    status: str = "new"
    sentiment: Optional[str] = None
    priority: str = "medium"
    inquiry_text: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[str] = None

class CRMStore:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self._init_schema()

    def _init_schema(self) -> None:
        with self.db.get_connection() as conn:
            conn.executescript(CRM_SCHEMA_SQL)
            conn.commit()

    def save_lead(self, lead: LeadRecord) -> None:
        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO crm_leads
                (id, name, email, phone, company, status, sentiment, priority, inquiry_text, notes, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    lead.id,
                    lead.name,
                    lead.email,
                    lead.phone,
                    lead.company,
                    lead.status,
                    lead.sentiment,
                    lead.priority,
                    lead.inquiry_text,
                    lead.notes,
                ),
            )
            conn.commit()

    def get_lead(self, lead_id: str) -> Optional[LeadRecord]:
        row = self.db.fetchone("SELECT * FROM crm_leads WHERE id = ?", (lead_id,))
        if not row:
            return None
        return LeadRecord(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            phone=row["phone"],
            company=row["company"],
            status=row["status"],
            sentiment=row["sentiment"],
            priority=row["priority"],
            inquiry_text=row["inquiry_text"],
            notes=row["notes"],
            created_at=row["created_at"],
        )

    def list_leads(self, status: Optional[str] = None, limit: int = 50) -> List[LeadRecord]:
        if status:
            rows = self.db.fetchall("SELECT * FROM crm_leads WHERE status = ? ORDER BY created_at DESC LIMIT ?", (status, limit))
        else:
            rows = self.db.fetchall("SELECT * FROM crm_leads ORDER BY created_at DESC LIMIT ?", (limit,))
        return [
            LeadRecord(
                id=r["id"],
                name=r["name"],
                email=r["email"],
                phone=r["phone"],
                company=r["company"],
                status=r["status"],
                sentiment=r["sentiment"],
                priority=r["priority"],
                inquiry_text=r["inquiry_text"],
                notes=r["notes"],
                created_at=r["created_at"],
            )
            for r in rows
        ]
