from typing import List
from ..models.checklist_model import ChecklistModel

class ChecklistService:
    SERVICE_REQUIREMENTS = {
        "ITR": [
            "PAN Card",
            "Aadhaar Card",
            "Bank Statement",
            "Form 16 / Salary Slips",
            "Investment Proofs"
        ],
        "GST": [
            "PAN Card",
            "GST Certificate",
            "Bank Statement",
            "Address Proof",
            "Authorization Letter"
        ],
        "Audit": [
            "PAN Card",
            "Aadhaar Card",
            "Bank Statement",
            "Balance Sheet",
            "P&L Statement",
            "GST Returns"
        ]
    }

    @classmethod
    def get_required_documents(cls, service_type: str) -> List[str]:
        return cls.SERVICE_REQUIREMENTS.get(service_type, cls.SERVICE_REQUIREMENTS["ITR"])

    @classmethod
    def initialize_client_checklist(cls, conn, client_id: str, service_type: str):
        required_docs = cls.get_required_documents(service_type)
        existing_items = ChecklistModel.get_by_client_id(conn, client_id)
        existing_types = {item["doc_type"] for item in existing_items}

        # Remove items from previous service that are not in new service and unfulfilled
        for item in existing_items:
            if item["doc_type"] not in required_docs and item["received"] == 0:
                conn.execute("DELETE FROM checklist WHERE id = ?", (item["id"],))

        # Add newly required checklist items
        for doc_type in required_docs:
            if doc_type not in existing_types:
                ChecklistModel.create_item(conn, client_id, doc_type, required=1)

    @classmethod
    def is_checklist_complete(cls, conn, client_id: str) -> bool:
        pending = ChecklistModel.count_pending(conn, client_id)
        return pending == 0
