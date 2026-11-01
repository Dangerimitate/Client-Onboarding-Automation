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
        for doc_type in required_docs:
            ChecklistModel.create_item(conn, client_id, doc_type, required=1)

    @classmethod
    def is_checklist_complete(cls, conn, client_id: str) -> bool:
        pending = ChecklistModel.count_pending(conn, client_id)
        return pending == 0
