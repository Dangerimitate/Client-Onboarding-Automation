from flask import Blueprint, jsonify, current_app
from ..extensions import get_db_connection
from ..models.document_model import DocumentModel
from ..models.message_model import MessageModel

stats_bp = Blueprint("stats_bp", __name__)

@stats_bp.route("/api/stats", methods=["GET"])
def get_dashboard_metrics():
    """Returns aggregated high-level business metrics for dashboard overview."""
    db_path = current_app.config["DB_PATH"]
    conn = get_db_connection(db_path)

    total_clients = conn.execute("SELECT COUNT(*) as c FROM clients").fetchone()["c"]
    by_status = {}
    for row in conn.execute("SELECT status, COUNT(*) as c FROM clients GROUP BY status"):
        by_status[row["status"]] = row["c"]

    total_docs = DocumentModel.count_total(conn)
    flagged_docs = DocumentModel.count_flagged(conn)
    pending_drafts = MessageModel.count_drafts(conn)

    conn.close()
    return jsonify({
        "total_clients": total_clients,
        "by_status": by_status,
        "total_documents": total_docs,
        "flagged_documents": flagged_docs,
        "pending_messages": pending_drafts
    })
