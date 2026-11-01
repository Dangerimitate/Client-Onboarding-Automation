import datetime
from typing import List
from ..models.client_model import ClientModel
from ..models.checklist_model import ChecklistModel
from ..models.message_model import MessageModel
from ..models.activity_model import ActivityModel

class NotificationService:
    @staticmethod
    def draft_followup_and_reminders(conn, client_id: str):
        """
        Auto-drafts follow-up Email and WhatsApp messages asking for missing documents,
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
        subject = f"Documents Required for {service} Onboarding – {name}"
        bullet_docs = "\n".join([f"  • {d}" for d in missing])
        email_body = f"""Dear {name},

Thank you for choosing our CA firm for your {service} requirements.

To proceed with your onboarding and file your compliance on time, we kindly request the following remaining documents:

{bullet_docs}

Please reply with the attached documents or upload them directly via our secure client portal.

Warm regards,
Client Onboarding Team
CA Firm & Associates"""

        if not MessageModel.exists_draft(conn, client_id, channel="email", status="draft"):
            MessageModel.create(conn, client_id, channel="email", subject=subject, body=email_body, status="draft")
            ActivityModel.log(conn, client_id, "message_drafted", f"Auto-drafted follow-up email for {len(missing)} missing documents.")

        # 2. WhatsApp Draft
        wa_docs = "\n".join([f"📄 {d}" for d in missing])
        wa_body = f"""Hi {name} 👋

Greetings from CA Firm & Associates! Regarding your {service} onboarding:

We are still awaiting the following documents to initiate your work:
{wa_docs}

Please share clear photos or PDF scans here at your convenience. Thank you! 🙏"""

        if not MessageModel.exists_draft(conn, client_id, channel="whatsapp", status="draft"):
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
