"""Local SQLite journal for Bodhisattva pauses.

One row per attempted email send. Stores draft, framing output, decision,
and the user's eventual choice. Hand-rolled SQL — no ORM — to stay
dependency-light and inspect easily.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS pauses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    draft TEXT NOT NULL,
    subject TEXT,
    recipient TEXT,
    recipient_context TEXT,
    wisdom_frame_json TEXT NOT NULL,
    decision TEXT NOT NULL,
    user_choice TEXT,
    final_sent_text TEXT,
    message_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_pauses_timestamp ON pauses(timestamp);
CREATE INDEX IF NOT EXISTS idx_pauses_recipient ON pauses(recipient);
"""


@dataclass
class PauseRecord:
    draft: str
    subject: str | None
    recipient: str | None
    recipient_context: str | None
    wisdom_frame_json: str
    decision: str
    id: int | None = None
    timestamp: str | None = None
    user_choice: str | None = None
    final_sent_text: str | None = None
    message_id: str | None = None


class Journal:
    def __init__(self, db_path: Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def create(self, record: PauseRecord) -> int:
        ts = record.timestamp or datetime.now(UTC).isoformat()
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO pauses (timestamp, draft, subject, recipient,
                                    recipient_context, wisdom_frame_json, decision)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ts,
                    record.draft,
                    record.subject,
                    record.recipient,
                    record.recipient_context,
                    record.wisdom_frame_json,
                    record.decision,
                ),
            )
            conn.commit()
            return int(cur.lastrowid)

    def get(self, record_id: int) -> PauseRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM pauses WHERE id = ?", (record_id,)
            ).fetchone()
        return _row_to_record(row) if row else None

    def list(self, limit: int = 50, recipient: str | None = None) -> list[PauseRecord]:
        query = "SELECT * FROM pauses"
        params: tuple = ()
        if recipient:
            query += " WHERE recipient = ?"
            params = (recipient,)
        query += " ORDER BY id DESC LIMIT ?"
        params = (*params, limit)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [_row_to_record(row) for row in rows]

    def update_user_choice(
        self,
        record_id: int,
        user_choice: str,
        final_sent_text: str | None = None,
        message_id: str | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE pauses
                SET user_choice = ?, final_sent_text = ?, message_id = ?
                WHERE id = ?
                """,
                (user_choice, final_sent_text, message_id, record_id),
            )
            conn.commit()


def _row_to_record(row: sqlite3.Row) -> PauseRecord:
    return PauseRecord(
        id=row["id"],
        timestamp=row["timestamp"],
        draft=row["draft"],
        subject=row["subject"],
        recipient=row["recipient"],
        recipient_context=row["recipient_context"],
        wisdom_frame_json=row["wisdom_frame_json"],
        decision=row["decision"],
        user_choice=row["user_choice"],
        final_sent_text=row["final_sent_text"],
        message_id=row["message_id"],
    )
