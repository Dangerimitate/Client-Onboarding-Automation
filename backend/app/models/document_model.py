import json
from typing import Dict, List, Optional
from ..utils import uid, now_iso

class DocumentModel:
    @staticmethod
    def get_by_client_id(conn, client_id: str) -> List[Dict]:
        rows = conn.execute(
            "SELECT * FROM documents WHERE client_id = ? ORDER BY uploaded_at DESC, rowid DESC",
            (client_id,)
        ).fetchall()
        docs = []
        seen_types = set()
        for r in rows:
            d = dict(r)
            d["extracted"] = json.loads(d["extracted"]) if d.get("extracted") else {}
            d["flags"] = json.loads(d["flags"]) if d.get("flags") else []
            dt = d.get("doc_type", "")
            # Return single authoritative document per recognized document type
            if dt and dt not in ("Unknown", "Electricity Bill"):
                if dt in seen_types:
                    continue
                seen_types.add(dt)
            docs.append(d)
        return docs

    @staticmethod
    def create(conn, client_id: str, doc_type: str, filename: str, filepath: str, extracted: Dict, confidence: float, flags: List) -> str:
        doc_id = uid()
        conn.execute(
            """INSERT INTO documents (id, client_id, doc_type, filename, filepath, extracted, confidence, flags, uploaded_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (doc_id, client_id, doc_type, filename, filepath, json.dumps(extracted), confidence, json.dumps(flags), now_iso())
        )
        return doc_id

    @staticmethod
    def count_total(conn) -> int:
        return conn.execute("SELECT COUNT(*) as c FROM documents").fetchone()["c"]

    @staticmethod
    def count_flagged(conn) -> int:
        return conn.execute("SELECT COUNT(*) as c FROM documents WHERE flags != '[]'").fetchone()["c"]
