from flask import Blueprint, jsonify, request, current_app
from ..extensions import get_db_connection
from ..models.client_model import ClientModel
from ..models.document_model import DocumentModel
from ..models.checklist_model import ChecklistModel
from ..models.message_model import MessageModel
from ..models.activity_model import ActivityModel

client_bp = Blueprint("client_bp", __name__)

@client_bp.route("/api/clients", methods=["GET"])
def get_clients():
    """Retrieve all clients with associated documents, checklist items, messages, and audit trail."""
    conn = get_db_connection(current_app.config["DB_PATH"])
    clients = ClientModel.get_all(conn)

    for c in clients:
        c_id = c["id"]
        c["documents"] = DocumentModel.get_by_client_id(conn, c_id)
        c["checklist"] = ChecklistModel.get_by_client_id(conn, c_id)
        c["messages"] = MessageModel.get_by_client_id(conn, c_id)
        c["activity"] = ActivityModel.get_by_client_id(conn, c_id)

    conn.close()
    return jsonify(clients)

@client_bp.route("/api/clients/<client_id>", methods=["GET"])
def get_client_by_id(client_id):
    """Retrieve detailed single client entity."""
    conn = get_db_connection(current_app.config["DB_PATH"])
    client = ClientModel.get_by_id(conn, client_id)
    if not client:
        conn.close()
        return jsonify({"error": "Client not found"}), 404

    client["documents"] = DocumentModel.get_by_client_id(conn, client_id)
    client["checklist"] = ChecklistModel.get_by_client_id(conn, client_id)
    client["messages"] = MessageModel.get_by_client_id(conn, client_id)
    client["activity"] = ActivityModel.get_by_client_id(conn, client_id)
    conn.close()
    return jsonify(client)

@client_bp.route("/api/clients/<client_id>/status", methods=["PUT"])
def update_status(client_id):
    """Update client onboarding status with audit logging."""
    data = request.get_json() or {}
    new_status = data.get("status")
    if not new_status:
        return jsonify({"error": "Status is required"}), 400

    conn = get_db_connection(current_app.config["DB_PATH"])
    client = ClientModel.get_by_id(conn, client_id)
    if not client:
        conn.close()
        return jsonify({"error": "Client not found"}), 404

    ClientModel.update_status(conn, client_id, new_status)
    ActivityModel.log(conn, client_id, "status_changed", f"Status changed to '{new_status}'")
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "status": new_status})

@client_bp.route("/api/checklist/<checklist_id>", methods=["PUT"])
def update_checklist_item(checklist_id):
    """
    Allows CA staff to manually mark a document checklist item as Verified (Correct / received = 1)
    or Rejected (Wrong / received = 0) to override OCR judgment mistakes.
    """
    data = request.get_json() or {}
    if "received" not in data:
        return jsonify({"error": "Field 'received' (0 or 1) is required."}), 400

    received = 1 if data["received"] in (1, True, "1") else 0
    reason = data.get("reason", "").strip()

    conn = get_db_connection(current_app.config["DB_PATH"])
    try:
        item = ChecklistModel.get_by_id(conn, checklist_id)
        if not item:
            return jsonify({"error": "Checklist item not found"}), 404

        client_id = item["client_id"]
        doc_type = item["doc_type"]

        ChecklistModel.update_item_status(conn, checklist_id, received)

        # Log CA staff human-in-the-loop override in audit trail
        status_label = "Verified (Correct)" if received == 1 else "Rejected (Wrong / Pending)"
        log_detail = f"Staff CA manually marked '{doc_type}' as {status_label} (Manual Override)."
        if reason:
            log_detail += f" Note: {reason}"
        ActivityModel.log(conn, client_id, "checklist_override", log_detail)

        # Re-evaluate client onboarding status
        from ..services.checklist_service import ChecklistService
        from ..services.notification_service import NotificationService
        
        is_complete = ChecklistService.is_checklist_complete(conn, client_id)
        client = ClientModel.get_by_id(conn, client_id)
        
        # Check if there are active blocking flags on documents
        doc_rows = DocumentModel.get_by_client_id(conn, client_id)
        has_critical = any(
            any(
                "invalid" in f.get("issue", "").lower() or
                "mismatch" in f.get("issue", "").lower() or
                "not accepted" in f.get("issue", "").lower() or
                "not an accepted" in f.get("issue", "").lower() or
                "unrecognized" in f.get("issue", "").lower() or
                f.get("field") == "scan_quality"
                for f in d.get("flags", [])
            )
            for d in doc_rows
        )

        if received == 0:
            # When marked Wrong: immediately draft / update follow-up email requesting re-submission
            NotificationService.draft_followup_and_reminders(conn, client_id, force_update_if_exists=True)

        if client and client["status"] == "onboarded":
            # If already onboarded, only update status if checklist becomes incomplete or flagged
            if not is_complete or has_critical:
                ClientModel.update_status(conn, client_id, "needs_review")
        else:
            if is_complete and not has_critical:
                ClientModel.update_status(conn, client_id, "ready_for_review")
                NotificationService.cancel_pending_reminders_if_complete(conn, client_id)
            elif is_complete and has_critical:
                ClientModel.update_status(conn, client_id, "needs_review")
            else:
                if client and client["status"] == "ready_for_review":
                    ClientModel.update_status(conn, client_id, "docs_pending")

        conn.commit()

        updated_item = ChecklistModel.get_by_id(conn, checklist_id)
        updated_client = ClientModel.get_by_id(conn, client_id)
        if updated_client:
            updated_client["messages"] = MessageModel.get_by_client_id(conn, client_id)
            updated_client["checklist"] = ChecklistModel.get_by_client_id(conn, client_id)
            updated_client["documents"] = DocumentModel.get_by_client_id(conn, client_id)
            updated_client["activity"] = ActivityModel.get_by_client_id(conn, client_id)

        return jsonify({
            "ok": True,
            "checklist_item": updated_item,
            "client": updated_client,
            "client_status": updated_client["status"] if updated_client else None,
            "message": f"'{doc_type}' marked as {status_label}."
        })
    finally:
        conn.close()
