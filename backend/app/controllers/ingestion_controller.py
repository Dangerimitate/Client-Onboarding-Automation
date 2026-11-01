import shutil
from flask import Blueprint, jsonify, current_app, send_from_directory
from ..extensions import get_db_connection
from ..services.ingestion_service import IngestionService

ingestion_bp = Blueprint("ingestion_bp", __name__)

@ingestion_bp.route("/api/ingest", methods=["POST"])
def ingest_emails():
    """Trigger email & document batch ingestion pipeline."""
    sample_dir = current_app.config["SAMPLE_DIR"]
    upload_dir = current_app.config["UPLOAD_DIR"]
    db_path = current_app.config["DB_PATH"]

    if not sample_dir.exists():
        return jsonify({"error": f"Sample pack directory not found at {sample_dir}"}), 404

    conn = get_db_connection(db_path)
    try:
        results = IngestionService.ingest_sample_pack(conn, sample_dir, upload_dir)
        return jsonify({
            "status": "success",
            "processed": len(results),
            "results": results
        })
    finally:
        conn.close()

@ingestion_bp.route("/api/reset", methods=["POST"])
def reset_database():
    """Reset database and storage for demo clean restart."""
    db_path = current_app.config["DB_PATH"]
    upload_dir = current_app.config["UPLOAD_DIR"]

    conn = get_db_connection(db_path)
    try:
        for table in ["clients", "documents", "checklist", "messages", "activity_log"]:
            conn.execute(f"DELETE FROM {table}")
        conn.commit()
    finally:
        conn.close()

    # Safely clear uploads directory (handling any OS file locks gracefully)
    if upload_dir.exists():
        for item in upload_dir.iterdir():
            if item.is_file():
                try:
                    item.unlink()
                except Exception:
                    pass

    return jsonify({"ok": True, "message": "Database and uploaded artifacts successfully reset."})

@ingestion_bp.route("/uploads/<path:filename>", methods=["GET"])
def serve_uploaded_document(filename):
    """Secure static file serve for uploaded/extracted documents."""
    upload_dir = current_app.config["UPLOAD_DIR"]
    return send_from_directory(str(upload_dir), filename)
