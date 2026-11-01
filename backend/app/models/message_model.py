from typing import Dict, List, Optional
from ..utils import uid, now_iso

class MessageModel:
    @staticmethod
    def get_by_client_id(conn, client_id: str) -> List[Dict]:
        rows = conn.execute(
            """SELECT * FROM messages 
               WHERE client_id = ? 
               ORDER BY 
                 CASE status 
                   WHEN 'draft' THEN 1 
                   WHEN 'approved' THEN 2 
                   WHEN 'scheduled' THEN 3 
                   ELSE 4 
                 END, 
                 created_at DESC""",
            (client_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def get_by_id(conn, message_id: str) -> Optional[Dict]:
        row = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,)).fetchone()
        return dict(row) if row else None

    @staticmethod
    def create(conn, client_id: str, channel: str, subject: str, body: str, status: str = "draft", scheduled_at: Optional[str] = None) -> str:
        msg_id = uid()
        conn.execute(
            """INSERT INTO messages (id, client_id, channel, subject, body, status, scheduled_at, approved_by, approved_at, sent_at, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?)""",
            (msg_id, client_id, channel, subject, body, status, scheduled_at, now_iso())
        )
        return msg_id

    @staticmethod
    def approve(conn, message_id: str, approver: str = "Staff"):
        conn.execute(
            "UPDATE messages SET status = 'approved', approved_by = ?, approved_at = ? WHERE id = ?",
            (approver, now_iso(), message_id)
        )

    @staticmethod
    def send(conn, message_id: str):
        conn.execute(
            "UPDATE messages SET status = 'sent', sent_at = ? WHERE id = ?",
            (now_iso(), message_id)
        )

    @staticmethod
    def reject(conn, message_id: str):
        conn.execute(
            "UPDATE messages SET status = 'rejected' WHERE id = ?",
            (message_id,)
        )

    @staticmethod
    def update_content(conn, message_id: str, subject: str, body: str):
        conn.execute(
            "UPDATE messages SET subject = ?, body = ? WHERE id = ?",
            (subject, body, message_id)
        )

    @staticmethod
    def exists_draft(conn, client_id: str, channel: str, status: str = "draft") -> bool:
        row = conn.execute(
            "SELECT id FROM messages WHERE client_id = ? AND channel = ? AND status = ?",
            (client_id, channel, status)
        ).fetchone()
        return row is not None

    @staticmethod
    def count_drafts(conn) -> int:
        return conn.execute("SELECT COUNT(*) as c FROM messages WHERE status = 'draft'").fetchone()["c"]
