import json
from typing import Dict, List, Optional
from ..utils import uid, now_iso

class ClientModel:
    @staticmethod
    def get_all(conn) -> List[Dict]:
        rows = conn.execute("SELECT * FROM clients ORDER BY created_at DESC").fetchall()
        result = []
        for r in rows:
            item = dict(r)
            item["flags"] = json.loads(item["flags"]) if item.get("flags") else []
            result.append(item)
        return result

    @staticmethod
    def get_by_id(conn, client_id: str) -> Optional[Dict]:
        row = conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
        if not row:
            return None
        item = dict(row)
        item["flags"] = json.loads(item["flags"]) if item.get("flags") else []
        return item

    @staticmethod
    def find_duplicate(conn, email: Optional[str] = None, pan: Optional[str] = None) -> Optional[Dict]:
        if email:
            row = conn.execute("SELECT id, name, email, status, service, pan FROM clients WHERE email = ?", (email,)).fetchone()
            if row:
                return dict(row)
        if pan:
            row = conn.execute("SELECT id, name, email, status, service, pan FROM clients WHERE pan = ?", (pan,)).fetchone()
            if row:
                return dict(row)
        return None

    @staticmethod
    def create(conn, name: str, email: str, phone: str, pan: str, aadhaar: str = "", gstin: str = "", service: str = "ITR", status: str = "new", flags: Optional[List] = None) -> str:
        client_id = uid()
        flags_json = json.dumps(flags or [])
        timestamp = now_iso()
        conn.execute(
            """INSERT INTO clients (id, name, email, phone, pan, aadhaar, gstin, service, status, flags, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (client_id, name, email, phone, pan, aadhaar, gstin, service, status, flags_json, timestamp, timestamp)
        )
        return client_id

    @staticmethod
    def update_status(conn, client_id: str, new_status: str):
        conn.execute(
            "UPDATE clients SET status = ?, updated_at = ? WHERE id = ?",
            (new_status, now_iso(), client_id)
        )

    @staticmethod
    def update_service(conn, client_id: str, new_service: str):
        conn.execute(
            "UPDATE clients SET service = ?, updated_at = ? WHERE id = ?",
            (new_service, now_iso(), client_id)
        )

    @staticmethod
    def update_flags(conn, client_id: str, flags: List):
        conn.execute(
            "UPDATE clients SET flags = ?, updated_at = ? WHERE id = ?",
            (json.dumps(flags), now_iso(), client_id)
        )
