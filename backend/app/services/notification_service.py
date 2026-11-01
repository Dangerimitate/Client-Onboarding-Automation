import datetime
from typing import List
from ..models.client_model import ClientModel
from ..models.checklist_model import ChecklistModel
from ..models.message_model import MessageModel
from ..models.activity_model import ActivityModel
from ..utils import now_iso

class NotificationService:
    @classmethod
    def draft_followup_and_reminders(cls, conn, client_id: str, force_update_if_exists: bool = False):
        """
        Auto-drafts follow-up Email and WhatsApp messages asking for missing or rejected documents,
        along with a scheduled reminder after 3 days.
        Crucial: All messages remain in 'draft' or 'scheduled' status until approved by staff.
        """
        client = ClientModel.get_by_id(conn, client_id)
        if not client:
            return

        missing = ChecklistModel.get_missing_doc_types(conn, client_id)
        if not missing:
            return

        name = client.get("name") or "Client"
        service = client.get("service") or "Requested Service"

        # 1. Email Draft
        subject = f"Action Required: Pending Documents for {service} Onboarding – {name}"
        bullet_docs = "\n".join([f"  • {d}" for d in missing])
        email_body = f"""Dear {name},

Thank you for choosing our CA firm for your {service} onboarding.

Our compliance team reviewed your submission and noticed that the following required document(s) are still pending verification or require a clear re-submission:

{bullet_docs}

Please reply directly to this email with updated attachments or upload them via the client portal at your earliest convenience so we can finalize your onboarding.

Warm regards,
Client Onboarding Team
CA Firm & Associates"""

        # 1. Email Draft: if already sent or approved, return it to 'draft' status with updated content
        existing_emails = conn.execute(
            "SELECT id, status FROM messages WHERE client_id = ? AND channel = 'email' ORDER BY created_at DESC",
            (client_id,)
        ).fetchall()

        if existing_emails:
            primary_id = existing_emails[0]["id"]
            prev_status = existing_emails[0]["status"]
            conn.execute(
                """UPDATE messages 
                   SET status = 'draft', subject = ?, body = ?, 
                       approved_by = NULL, approved_at = NULL, sent_at = NULL, created_at = ?
                   WHERE id = ?""",
                (subject, email_body, now_iso(), primary_id)
            )
            # Remove any duplicate email rows for this client to keep communications clean
            for extra in existing_emails[1:]:
                conn.execute("DELETE FROM messages WHERE id = ?", (extra["id"],))

            if prev_status == "sent":
                ActivityModel.log(conn, client_id, "message_drafted", f"Returned sent email back to draft: New rejected/pending documents required ({', '.join(missing)}).")
            else:
                ActivityModel.log(conn, client_id, "message_updated", f"Updated follow-up email draft with {len(missing)} pending/rejected documents ({', '.join(missing)}).")
        else:
            MessageModel.create(conn, client_id, channel="email", subject=subject, body=email_body, status="draft")
            ActivityModel.log(conn, client_id, "message_drafted", f"Auto-drafted follow-up email for {len(missing)} pending/rejected documents ({', '.join(missing)}).")

        # 2. WhatsApp Draft
        wa_docs = "\n".join([f"📄 {d}" for d in missing])
        wa_body = f"""Hi {name} 👋

Greetings from CA Firm & Associates! Regarding your {service} onboarding:

We are still awaiting the following documents to initiate your work:
{wa_docs}

Please share clear photos or PDF scans here at your convenience. Thank you! 🙏"""

        existing_was = conn.execute(
            "SELECT id, status FROM messages WHERE client_id = ? AND channel = 'whatsapp' ORDER BY created_at DESC",
            (client_id,)
        ).fetchall()

        if existing_was:
            primary_wa_id = existing_was[0]["id"]
            conn.execute(
                """UPDATE messages 
                   SET status = 'draft', subject = ?, body = ?, 
                       approved_by = NULL, approved_at = NULL, sent_at = NULL, created_at = ?
                   WHERE id = ?""",
                (f"WhatsApp Reminder – {name}", wa_body, now_iso(), primary_wa_id)
            )
            for extra in existing_was[1:]:
                conn.execute("DELETE FROM messages WHERE id = ?", (extra["id"],))
        else:
            MessageModel.create(conn, client_id, channel="whatsapp", subject=f"WhatsApp Reminder – {name}", body=wa_body, status="draft")

        # 3. Scheduled Follow-up Reminder (3 days later)
        reminder_time = (datetime.datetime.now() + datetime.timedelta(days=3)).isoformat()
        if not MessageModel.exists_draft(conn, client_id, channel="email", status="scheduled"):
            reminder_body = f"""Dear {name},

This is a gentle reminder regarding pending documents for your {service} filing:

{bullet_docs}

Kindly share these documents so our team can review and avoid any deadline penalties.

Best regards,
Client Onboarding Team
CA Firm & Associates"""
            MessageModel.create(conn, client_id, channel="email", subject=f"Follow-up: Pending Documents for {service} – {name}", body=reminder_body, status="scheduled", scheduled_at=reminder_time)

    @classmethod
    def sync_and_verify_before_trigger(cls, conn, message_id: str) -> dict:
        """
        Re-verifies client document checklist immediately before a scheduled reminder
        or follow-up message is triggered, approved, or sent:
        1. If ALL documents are now received: Auto-cancels the reminder (so client isn't bugged).
        2. If SOME documents were received in the interim: Dynamically updates the body text
           so it only asks for the still-missing documents.
        """
        msg = MessageModel.get_by_id(conn, message_id)
        if not msg:
            return {"ok": False, "error": "Message not found"}

        client_id = msg["client_id"]
        client = ClientModel.get_by_id(conn, client_id)
        if not client:
            return {"ok": False, "error": "Client not found"}

        missing = ChecklistModel.get_missing_doc_types(conn, client_id)
        name = client.get("name") or "Client"
        service = client.get("service") or "Requested Service"

        # Case 1: All documents have already been received!
        if not missing:
            MessageModel.reject(conn, message_id)
            ActivityModel.log(
                conn, client_id, "reminder_cancelled",
                f"Auto-cancelled {msg['channel'].title()} reminder: All checklist documents have already been received."
            )
            return {
                "ok": False,
                "all_received": True,
                "missing_count": 0,
                "reason": "All required documents for this client have already been received. Reminder has been automatically cancelled."
            }

        # Case 2: Update the draft to reflect only currently missing documents
        bullet_docs = "\n".join([f"  • {d}" for d in missing])
        if msg["channel"] == "email":
            updated_body = f"""Dear {name},

This is a gentle reminder regarding pending documents for your {service} filing:

{bullet_docs}

Kindly share these documents so our team can review and avoid any deadline penalties.

Best regards,
Client Onboarding Team
CA Firm & Associates"""
        else:
            wa_docs = "\n".join([f"📄 {d}" for d in missing])
            updated_body = f"""Hi {name} 👋

Greetings from CA Firm & Associates! Regarding your {service} onboarding:

We are still awaiting the following documents to initiate your work:
{wa_docs}

Please share clear photos or PDF scans here at your convenience. Thank you! 🙏"""

        MessageModel.update_content(conn, message_id, msg["subject"], updated_body)
        ActivityModel.log(
            conn, client_id, "reminder_rechecked",
            f"Pre-send checklist check: Verified {len(missing)} documents still pending ({', '.join(missing)})."
        )

        return {
            "ok": True,
            "all_received": False,
            "missing_count": len(missing),
            "missing_docs": missing
        }

    @classmethod
    def cancel_pending_reminders_if_complete(cls, conn, client_id: str):
        """
        Cancels all pending draft or scheduled reminders if the client's checklist is 100% complete.
        """
        rows = conn.execute(
            "SELECT id, channel FROM messages WHERE client_id = ? AND status IN ('draft', 'scheduled')",
            (client_id,)
        ).fetchall()
        for r in rows:
            MessageModel.reject(conn, r["id"])
            ActivityModel.log(
                conn, client_id, "reminder_auto_resolved",
                f"Auto-resolved {r['channel'].title()} reminder: All required checklist documents received."
            )
