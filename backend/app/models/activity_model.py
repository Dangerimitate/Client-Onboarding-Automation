from typing import Dict, List
from ..utils import uid, now_iso

class ActivityModel:
    @staticmethod
    def log(conn, client_id: str, action: str, detail: str = ""):
        conn.execute(
            "INSERT INTO activity_log (id, client_id, action, detail, created_at) VALUES (?, ?, ?, ?, ?)",
            (uid(), client_id, action, detail, now_iso())
        )

    @staticmethod
    def get_by_client_id(conn, client_id: str) -> List[Dict]:
        rows = conn.execute("SELECT * FROM activity_log WHERE client_id = ? ORDER BY created_at", (client_id,)).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def get_recent(conn, limit: int = 50) -> List[Dict]:
        rows = conn.execute("SELECT * FROM activity_log ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
