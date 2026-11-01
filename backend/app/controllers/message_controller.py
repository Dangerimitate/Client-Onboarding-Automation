from flask import Blueprint, jsonify, request, current_app
from ..extensions import get_db_connection
from ..models.client_model import ClientModel
from ..models.message_model import MessageModel
from ..models.activity_model import ActivityModel
from ..services.notification_service import NotificationService
from ..services.email_sender_service import EmailSenderService
import urllib.parse

message_bp = Blueprint("message_bp", __name__)

@message_bp.route("/api/messages/<msg_id>/approve", methods=["POST"])
def approve_message(msg_id):
    """Staff approval endpoint. Re-checks documents and moves draft to approved status."""
    data = request.get_json() or {}
    approver = data.get("approver", "Senior Staff")

    conn = get_db_connection(current_app.config["DB_PATH"])
    msg = MessageModel.get_by_id(conn, msg_id)
    if not msg:
        conn.close()
        return jsonify({"error": "Message not found"}), 404

    # Dynamic pre-approval document verification
    check = NotificationService.sync_and_verify_before_trigger(conn, msg_id)
    if check.get("all_received"):
        conn.commit()
        conn.close()
        return jsonify({
            "ok": False,
            "all_received": True,
            "error": "All required documents have already been received for this client. The reminder has been automatically cancelled."
        }), 400

    MessageModel.approve(conn, msg_id, approver)
    ActivityModel.log(
        conn, msg["client_id"], "message_approved",
        f"{msg['channel'].title()} message approved by {approver} ({check.get('missing_count', 0)} docs pending)"
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "message_id": msg_id, "status": "approved"})

@message_bp.route("/api/messages/<msg_id>/send", methods=["POST"])
def send_message(msg_id):
    """
    Sends message to client. Strict guards:
    1. MUST BE APPROVED by staff first.
    2. Dynamically re-checks required documents before triggering send!
    """
    conn = get_db_connection(current_app.config["DB_PATH"])
    msg = MessageModel.get_by_id(conn, msg_id)
    if not msg:
        conn.close()
        return jsonify({"error": "Message not found"}), 404

    if msg["status"] != "approved":
        conn.close()
        return jsonify({
            "error": "Human Approval Required: Message must be explicitly approved by staff before sending."
        }), 400

    # Dynamic pre-send document verification
    check = NotificationService.sync_and_verify_before_trigger(conn, msg_id)
    if check.get("all_received"):
        conn.commit()
        conn.close()
        return jsonify({
            "ok": False,
            "all_received": True,
            "error": "Action Blocked: All required documents have already been received! Reminder was automatically cancelled."
        }), 400

    client = ClientModel.get_by_id(conn, msg["client_id"])
    channel = (msg["channel"] or "email").lower()

    if channel == "email":
        # Retrieve firm mail server credentials from inbox_settings
        settings_row = conn.execute("SELECT * FROM inbox_settings WHERE id = 1").fetchone()
        if not settings_row or not settings_row["username"] or not settings_row["password"]:
            conn.close()
            return jsonify({
                "ok": False,
                "error": "Mail server credentials not configured. Please open 'Email Setup' in the dashboard, enter your firm email & App Password, and save."
            }), 400

        settings = dict(settings_row)
        smtp_host, smtp_port, use_tls = EmailSenderService.get_smtp_host_and_port(
            provider=settings.get("provider", ""),
            imap_host=settings.get("host", "")
        )

        recipient_email = client.get("email") if client else ""
        if not recipient_email or "@" not in recipient_email:
            conn.close()
            return jsonify({
                "ok": False,
                "error": f"Client '{client.get('name') if client else ''}' has no valid email address."
            }), 400

        # Attempt real live SMTP delivery
        success, err = EmailSenderService.send_live_email(
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            username=settings["username"],
            password=settings["password"],
            to_email=recipient_email,
            subject=msg["subject"],
            body_text=msg["body"],
            use_tls=use_tls
        )

        if not success:
            conn.close()
            return jsonify({
                "ok": False,
                "error": err
            }), 500

        # Mark message as sent in database
        MessageModel.send(conn, msg_id)
        ActivityModel.log(
            conn, msg["client_id"], "message_sent",
            f"Live email delivered via {smtp_host} to {recipient_email}. Subject: '{msg['subject']}'"
        )
        conn.commit()
        conn.close()

        return jsonify({
            "ok": True,
            "status": "sent",
            "simulated": False,
            "recipient": recipient_email,
            "message": f"Email successfully delivered to {recipient_email} via {smtp_host}!"
        })

    elif channel == "whatsapp":
        phone = client.get("phone") if client else ""
        clean_phone = "".join(filter(str.isdigit, phone or ""))
        wa_url = None
        
        if clean_phone:
            # Auto-format 10-digit mobile numbers with India country code (91)
            if len(clean_phone) == 10:
                clean_phone = "91" + clean_phone
            elif clean_phone.startswith("0") and len(clean_phone) == 11:
                clean_phone = "91" + clean_phone[1:]

            encoded_body = urllib.parse.quote(msg["body"])
            wa_url = f"https://wa.me/{clean_phone}?text={encoded_body}"

        MessageModel.send(conn, msg_id)
        ActivityModel.log(
            conn, msg["client_id"], "message_sent",
            f"WhatsApp follow-up dispatched for {client.get('name') or 'client'} ({phone or 'No phone'})."
        )
        conn.commit()
        conn.close()

        recipient_display = f" ({phone})" if phone else ""
        return jsonify({
            "ok": True,
            "status": "sent",
            "channel": "whatsapp",
            "whatsapp_url": wa_url,
            "message": f"WhatsApp follow-up ready for {client.get('name') or 'Client'}{recipient_display}. Opening WhatsApp Web with pre-filled missing documents checklist."
        })

    else:
        MessageModel.send(conn, msg_id)
        conn.commit()
        conn.close()
        return jsonify({"ok": True, "status": "sent"})

@message_bp.route("/api/messages/<msg_id>/reject", methods=["POST"])
def reject_message(msg_id):
    """Rejects an auto-drafted message."""
    conn = get_db_connection(current_app.config["DB_PATH"])
    msg = MessageModel.get_by_id(conn, msg_id)
    if not msg:
        conn.close()
        return jsonify({"error": "Message not found"}), 404

    MessageModel.reject(conn, msg_id)
    ActivityModel.log(
        conn, msg["client_id"], "message_rejected",
        f"{msg['channel'].title()} draft rejected by staff"
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "status": "rejected"})

@message_bp.route("/api/messages/<msg_id>", methods=["PUT"])
def edit_message(msg_id):
    """Staff edits the subject and body of an auto-drafted message."""
    data = request.get_json() or {}
    subject = data.get("subject", "")
    body = data.get("body", "")

    conn = get_db_connection(current_app.config["DB_PATH"])
    msg = MessageModel.get_by_id(conn, msg_id)
    if not msg:
        conn.close()
        return jsonify({"error": "Message not found"}), 404

    MessageModel.update_content(conn, msg_id, subject, body)
    ActivityModel.log(
        conn, msg["client_id"], "message_edited",
        f"{msg['channel'].title()} message draft edited by staff"
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "status": "edited"})
