
from typing import Dict, List, Optional
from ..utils import uid

class ChecklistModel:
    @staticmethod
    def get_by_client_id(conn, client_id: str) -> List[Dict]:
        rows = conn.execute("SELECT * FROM checklist WHERE client_id = ?", (client_id,)).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def create_item(conn, client_id: str, doc_type: str, required: int = 1) -> str:
        chk_id = uid()
        conn.execute(
            "INSERT INTO checklist (id, client_id, doc_type, required, received, doc_id) VALUES (?, ?, ?, ?, 0, NULL)",
            (chk_id, client_id, doc_type, required)
        )
        return chk_id

    @staticmethod
    def mark_received(conn, client_id: str, doc_type: str, doc_id: str):
        conn.execute(
            "UPDATE checklist SET received = 1, doc_id = ? WHERE client_id = ? AND doc_type = ?",
            (doc_id, client_id, doc_type)
        )

    @staticmethod
    def get_by_id(conn, checklist_id: str) -> Optional[Dict]:
        row = conn.execute("SELECT * FROM checklist WHERE id = ?", (checklist_id,)).fetchone()
        return dict(row) if row else None

    @staticmethod
    def update_item_status(conn, checklist_id: str, received: int, doc_id: Optional[str] = None):
        if doc_id:
            conn.execute(
                "UPDATE checklist SET received = ?, doc_id = ? WHERE id = ?",
                (received, doc_id, checklist_id)
            )
        else:
            conn.execute(
                "UPDATE checklist SET received = ? WHERE id = ?",
                (received, checklist_id)
            )

    @staticmethod
    def count_pending(conn, client_id: str) -> int:
        row = conn.execute(
            "SELECT COUNT(*) as c FROM checklist WHERE client_id = ? AND received = 0",
            (client_id,)
        ).fetchone()
        return row["c"] if row else 0

    @staticmethod
    def get_missing_doc_types(conn, client_id: str) -> List[str]:
        rows = conn.execute(
            "SELECT doc_type FROM checklist WHERE client_id = ? AND received = 0",
            (client_id,)
        ).fetchall()
        return [r["doc_type"] for r in rows]
