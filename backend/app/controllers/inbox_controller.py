from flask import Blueprint, jsonify, request, current_app
from ..extensions import get_db_connection
from ..services.email_inbox_service import EmailInboxService
from ..services.email_sender_service import EmailSenderService
from ..services.ingestion_service import IngestionService

inbox_bp = Blueprint("inbox_bp", __name__)

@inbox_bp.route("/api/inbox/settings", methods=["GET"])
def get_inbox_settings():
    """Retrieve current email inbox configuration and presets."""
    db_path = current_app.config["DB_PATH"]
    conn = get_db_connection(db_path)
    try:
        settings = EmailInboxService.get_settings(conn)
        return jsonify({
            "settings": settings,
            "presets": EmailInboxService.PRESETS
        })
    finally:
        conn.close()

@inbox_bp.route("/api/inbox/settings", methods=["POST"])
def save_inbox_settings():
    """Save or update email inbox configuration."""
    data = request.get_json() or {}
    db_path = current_app.config["DB_PATH"]
    conn = get_db_connection(db_path)
    try:
        EmailInboxService.save_settings(conn, data)
        updated = EmailInboxService.get_settings(conn)
        return jsonify({
            "ok": True,
            "message": "Inbox settings saved successfully.",
            "settings": updated
        })
    finally:
        conn.close()

@inbox_bp.route("/api/inbox/test", methods=["POST"])
def test_inbox_connection():
    """Test connection to live IMAP mail server."""
    data = request.get_json() or {}
    db_path = current_app.config["DB_PATH"]
    conn = get_db_connection(db_path)

    host = data.get("host", "").strip()
    port = int(data.get("port", 993))
    username = data.get("username", "").strip()
    password = data.get("password", "")
    use_ssl = bool(data.get("use_ssl", True))
    folder = data.get("folder", "INBOX").strip() or "INBOX"

    # If password not provided in test body, check if already saved in DB
    if not password:
        row = conn.execute("SELECT password FROM inbox_settings WHERE id = 1").fetchone()
        if row and row["password"]:
            password = row["password"]

    conn.close()

    result = EmailInboxService.test_connection(
        host=host,
        port=port,
        username=username,
        password=password,
        use_ssl=use_ssl,
        folder=folder
    )

    # If IMAP test succeeded, also test outbound SMTP
    if result.get("ok"):
        provider = data.get("provider", "custom")
        smtp_host, smtp_port, use_tls = EmailSenderService.get_smtp_host_and_port(provider, host)
        smtp_ok, smtp_err = EmailSenderService.test_smtp_connection(
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            username=username,
            password=password,
            use_tls=use_tls
        )
        if smtp_ok:
            result["message"] = f"Connected successfully! Inbound IMAP ({host}) and Outbound SMTP ({smtp_host}) verified."
            result["smtp_ok"] = True
        else:
            result["message"] = f"Inbound IMAP ({host}) connected, but Outbound SMTP ({smtp_host}) failed: {smtp_err}"
            result["smtp_ok"] = False

    status_code = 200 if result.get("ok") else 400
    return jsonify(result), status_code

@inbox_bp.route("/api/inbox/sync", methods=["POST"])
def sync_live_inbox():
    """Trigger live synchronization from production mail server."""
    db_path = current_app.config["DB_PATH"]
    upload_dir = current_app.config["UPLOAD_DIR"]
    data = request.get_json() or {}
    limit = int(data.get("limit", 10))
    mark_seen = bool(data.get("mark_seen", False))

    conn = get_db_connection(db_path)
    try:
        sync_result = IngestionService.sync_live_inbox(
            conn=conn,
            upload_dir=upload_dir,
            limit=limit,
            mark_seen=mark_seen
        )
        status_code = 200 if sync_result.get("ok") else 400
        return jsonify(sync_result), status_code
    finally:
        conn.close()
