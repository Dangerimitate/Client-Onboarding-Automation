import re
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional
from ..utils import now_iso
from ..utils.validators import validate_pan
from ..models.client_model import ClientModel
from ..models.document_model import DocumentModel
from ..models.checklist_model import ChecklistModel
from ..models.activity_model import ActivityModel
from .ocr_service import OCRService
from .checklist_service import ChecklistService
from .notification_service import NotificationService
from .email_inbox_service import EmailInboxService

class IngestionService:
    @staticmethod
    def parse_sample_emails_file(file_path: Path) -> List[Dict[str, Any]]:
        if not file_path.exists():
            return []
        lines = file_path.read_text(encoding="utf-8").splitlines()
        emails_parsed = []
        current = {}

        for line in lines:
            line = line.strip()
            if not line or line.startswith("All values"):
                if current:
                    emails_parsed.append(current)
                    current = {}
                continue
            m = re.match(r'Email\s+(\d+)\s*(\([^)]*\))?\s*\|\s*From:\s*(\S+)\s*\|\s*Attachments:\s*(.+)', line)
            if m:
                current = {
                    "email_num": int(m.group(1)),
                    "note": (m.group(2) or "").strip("() "),
                    "from": m.group(3),
                    "attachments": [a.strip() for a in m.group(4).split(",") if a.strip()],
                    "body": ""
                }
            elif current:
                current["body"] = line

        if current:
            emails_parsed.append(current)
        return emails_parsed

    @staticmethod
    def extract_client_info_from_email(body: str, default_name: str = "", default_service: str = "") -> Dict[str, Any]:
        name, pan, phone, service, gstin = default_name or "", "", "", default_service or "", ""

        nm = re.search(r"I'm\s+([A-Za-z ]+?)(?:,|\.|$)", body)
        if nm:
            name = nm.group(1).strip()
        if not name:
            nm = re.search(r"^([A-Za-z ]+?)\s+(?:here|traders)", body, re.IGNORECASE)
            if nm:
                name = nm.group(1).strip()

        # Extract PAN: strictly match 10-character standard PAN format (e.g. ABCDE1234F)
        pm = re.search(r'\b([A-Za-z]{5}[0-9]{4}[A-Za-z])\b', body)
        if pm:
            pan = pm.group(1).strip().upper()
        else:
            pm = re.search(r'PAN[:\s]+([A-Za-z0-9]+)', body, re.IGNORECASE)
            if pm and validate_pan(pm.group(1).strip()):
                pan = pm.group(1).strip().upper()

        ph = re.search(r'(?:phone|call|mob|contact)\s*([\d ]+)', body, re.IGNORECASE)
        if ph:
            phone = re.sub(r'\s', '', ph.group(1))

        if not service:
            # Strict Service Filter: only detect GST, ITR, or Audit
            if re.search(r'\b(gst|gstin|gstr|gstr1|gstr3b|goods\s+and\s+services?\s+tax)\b', body, re.IGNORECASE):
                service = "GST"
            elif re.search(r'\b(itr|itr1|itr2|itr3|itr4|income\s*tax|tax\s*return|tax\s*filing|form\s*16|form\s*26as|salary\s*slip)\b', body, re.IGNORECASE):
                service = "ITR"
            elif re.search(r'\b(audit|auditing|tax\s*audit|statutory\s*audit|internal\s*audit|balance\s*sheet|p&l)\b', body, re.IGNORECASE):
                service = "Audit"

        gm = re.search(r'GSTIN\s+(\S+)', body, re.IGNORECASE)
        if gm:
            gstin = gm.group(1).strip().upper()

        return {
            "name": name or "New Client",
            "pan": pan,
            "phone": phone,
            "service": service,
            "gstin": gstin
        }

    @classmethod
    def process_single_email(
        cls,
        conn,
        sender: str,
        body: str,
        attachments: List[Any],
        upload_dir: Path,
        source_label: str = "Email",
        sample_dir: Optional[Path] = None,
        default_name: str = "",
        service_hint: str = ""
    ) -> Dict[str, Any]:
        """
        Unified ingestion worker for both sample folder attachments and direct live IMAP attachments.
        """
        client_info = cls.extract_client_info_from_email(body, default_name=default_name, default_service=service_hint)
        service = client_info["service"]
        pan = client_info["pan"]

        # Duplicate detection check (existing client sending follow-up documents)
        duplicate = ClientModel.find_duplicate(conn, email=sender, pan=pan if pan else None)
        if duplicate:
            if not service:
                service = duplicate.get("service") or ""
            if not pan and duplicate.get("pan"):
                pan = duplicate.get("pan") or ""

        # Filter safeguard: Must be GST, ITR, or Audit (either newly requested or existing client service)
        if not service:
            return {
                "source": source_label,
                "from": sender,
                "status": "skipped",
                "reason": "Email filtered out: Does not match required services (GST, ITR, Audit).",
                "client_id": None,
                "flags": []
            }

        result = {
            "source": source_label,
            "from": sender,
            "status": "ok",
            "flags": [],
            "client_id": None
        }

        if duplicate:
            client_id = duplicate["id"]
            result["client_id"] = client_id
            result["status"] = "duplicate_merged"
            result["flags"].append({
                "type": "duplicate",
                "message": f"Duplicate client detected – matches existing record '{duplicate['name']}' (ID: {duplicate['id']}). Merged new attachments."
            })
            ActivityModel.log(conn, client_id, "duplicate_merged", f"Merged attachments from {source_label} ({sender})")
        else:
            client_flags = []
            if pan and not validate_pan(pan):
                client_flags.append({
                    "field": "pan",
                    "issue": f"Invalid PAN format: '{pan}'. Expected AAAAA9999A format."
                })

            client_id = ClientModel.create(
                conn=conn,
                name=client_info["name"],
                email=sender,
                phone=client_info["phone"],
                pan=pan,
                gstin=client_info["gstin"],
                service=client_info["service"],
                status="new",
                flags=client_flags
            )
            result["client_id"] = client_id
            ActivityModel.log(conn, client_id, "created", f"Client record created from {source_label} ({sender})")

            # Build service-specific checklist
            ChecklistService.initialize_client_checklist(conn, client_id, client_info["service"])

        upload_dir.mkdir(parents=True, exist_ok=True)

        existing_doc_rows = DocumentModel.get_by_client_id(conn, client_id)
        already_ingested_files = {d["filename"] for d in existing_doc_rows}
        new_attachments_processed = 0

        # Process incoming attachments
        for att in attachments:
            if isinstance(att, str):
                att_file = att
            elif isinstance(att, dict):
                att_file = att.get("filename", "")
            else:
                continue

            if not att_file:
                continue

            # Prevent duplicate re-ingestion if this attachment filename was already processed for this client
            if att_file in already_ingested_files:
                continue

            already_ingested_files.add(att_file)

            if isinstance(att, str):
                # String filename from sample_pack
                if not sample_dir:
                    continue
                att_path = sample_dir / att_file
                if not att_path.exists():
                    result["flags"].append({"type": "missing_file", "message": f"Attachment not found: {att_file}"})
                    continue
                dest = upload_dir / f"{client_id}_{att_file}"
                shutil.copy2(str(att_path), str(dest))
            elif isinstance(att, dict):
                # Live attachment bytes from IMAP
                dest = upload_dir / f"{client_id}_{att_file}"
                with open(dest, "wb") as f:
                    f.write(att["bytes"])

            new_attachments_processed += 1

            # Run OCR extraction & field validation
            doc_type, fields, confidence, doc_flags = OCRService.process_document(
                filename=att_file,
                expected_pan=pan,
                filepath=str(dest)
            )

            doc_id = DocumentModel.create(
                conn=conn,
                client_id=client_id,
                doc_type=doc_type,
                filename=att_file,
                filepath=str(dest),
                extracted=fields,
                confidence=confidence,
                flags=doc_flags
            )

            ActivityModel.log(
                conn, client_id, "document_uploaded",
                f"{doc_type} processed ({att_file}), extraction confidence: {confidence:.0%}"
            )

            # Determine if document has blocking errors that prevent checklist fulfillment
            has_fatal_doc_error = any(
                "invalid" in f.get("issue", "").lower() or
                "mismatch" in f.get("issue", "").lower() or
                "not accepted" in f.get("issue", "").lower() or
                "not an accepted" in f.get("issue", "").lower() or
                "unrecognized" in f.get("issue", "").lower()
                for f in doc_flags
            )

            # Update checklist only if recognized, accepted, and valid document
            if doc_type not in ("Electricity Bill", "Unknown") and not has_fatal_doc_error:
                ChecklistModel.mark_received(conn, client_id, doc_type, doc_id)
            elif has_fatal_doc_error:
                err_detail = doc_flags[0].get("issue") if doc_flags else "Validation failed"
                ActivityModel.log(
                    conn, client_id, "document_flagged",
                    f"{doc_type} flagged with verification issues ({att_file}): {err_detail}"
                )

            if doc_flags:
                result["flags"].extend([{"type": "doc_flag", "doc": att_file, **f} for f in doc_flags])

        # Determine client status
        all_flags = result["flags"]
        # Check all documents for this client in DB to ensure persistent awareness of any flags
        existing_doc_rows = DocumentModel.get_by_client_id(conn, client_id)
        all_doc_flags = []
        for d in existing_doc_rows:
            if d.get("flags"):
                for f in d["flags"]:
                    all_doc_flags.append(f)

        combined_flags = all_flags + all_doc_flags

        has_critical = any(
            "invalid" in f.get("issue", "").lower() or
            "mismatch" in f.get("issue", "").lower() or
            "not accepted" in f.get("issue", "").lower() or
            "not an accepted" in f.get("issue", "").lower() or
            "unrecognized" in f.get("issue", "").lower() or
            f.get("field") == "scan_quality" or
            ("scan_quality" in str(f))
            for f in combined_flags
        )

        # Update client table flags for UI visibility
        active_client_flags = [f for f in combined_flags if f.get("issue")]
        seen_issues = set()
        deduped_flags = []
        for f in active_client_flags:
            iss = f.get("issue", "")
            if iss and iss not in seen_issues:
                seen_issues.add(iss)
                deduped_flags.append(f)
        ClientModel.update_flags(conn, client_id, deduped_flags)

        # Check current client status before modifying to preserve completed onboarding
        curr_client = ClientModel.get_by_id(conn, client_id)
        current_status = curr_client.get("status") if curr_client else "new"

        if current_status == "onboarded":
            # Client has already been fully onboarded by CA staff.
            # Never demote their status back to ready_for_review, needs_review, or docs_pending!
            pass
        elif has_critical:
            ClientModel.update_status(conn, client_id, "needs_review")
        else:
            if ChecklistService.is_checklist_complete(conn, client_id):
                ClientModel.update_status(conn, client_id, "ready_for_review")
                # Auto-cancel any outstanding draft/scheduled reminders since client fulfilled all documents
                NotificationService.cancel_pending_reminders_if_complete(conn, client_id)
            else:
                if not duplicate:
                    ClientModel.update_status(conn, client_id, "new")
                else:
                    ClientModel.update_status(conn, client_id, "docs_pending")

        return result

    @classmethod
    def ingest_sample_pack(cls, conn, sample_dir: Path, upload_dir: Path) -> List[Dict]:
        email_file = sample_dir / "sample_emails.txt"
        emails = cls.parse_sample_emails_file(email_file)
        results = []

        for em in emails:
            res = cls.process_single_email(
                conn=conn,
                sender=em["from"],
                body=em["body"],
                attachments=em["attachments"],
                upload_dir=upload_dir,
                source_label=f"Sample Email #{em['email_num']}",
                sample_dir=sample_dir
            )
            results.append(res)

        conn.commit()

        # Generate auto-drafted follow-up messages for clients with pending docs
        for r in results:
            if r["client_id"]:
                NotificationService.draft_followup_and_reminders(conn, r["client_id"])

        conn.commit()
        return results

    @classmethod
    def sync_live_inbox(cls, conn, upload_dir: Path, limit: int = 10, mark_seen: bool = False) -> Dict[str, Any]:
        """
        Executes a direct live sync from the configured production mail server (IMAP).
        """
        row = conn.execute("SELECT * FROM inbox_settings WHERE id = 1").fetchone()
        if not row or not row["host"] or not row["username"] or not row["password"]:
            return {
                "ok": False,
                "error": "Mail server credentials not configured. Please configure your email inbox in Settings."
            }

        settings = dict(row)
        emails, err = EmailInboxService.fetch_live_emails(
            host=settings["host"],
            port=settings["port"],
            username=settings["username"],
            password=settings["password"],
            use_ssl=bool(settings["use_ssl"]),
            folder=settings["folder"] or "INBOX",
            upload_dir=upload_dir,
            limit=limit,
            mark_seen=mark_seen,
            conn=conn
        )

        if err:
            return {"ok": False, "error": f"Failed to sync with live mail server: {err}"}

        if not emails:
            # Update last synced time
            conn.execute("UPDATE inbox_settings SET last_synced = ? WHERE id = 1", (now_iso(),))
            conn.commit()
            return {
                "ok": True,
                "processed": 0,
                "message": f"Connected to {settings['host']} successfully. No new unread onboarding emails found.",
                "results": []
            }

        results = []
        skipped_count = 0
        for em in emails:
            # Check service matching: GST, ITR, or Audit
            service = em.get("service") or EmailInboxService.match_service_intent(
                em.get("subject", ""),
                em.get("body", ""),
                em.get("attachments", [])
            )
            if not service:
                skipped_count += 1
                continue

            res = cls.process_single_email(
                conn=conn,
                sender=em["from"],
                body=em["body"],
                attachments=em["attachments"],
                upload_dir=upload_dir,
                source_label=f"Live IMAP Email: '{em['subject']}'",
                default_name=em.get("sender_name", ""),
                service_hint=service
            )
            if res.get("status") == "skipped":
                skipped_count += 1
            else:
                results.append(res)

        conn.execute("UPDATE inbox_settings SET last_synced = ? WHERE id = 1", (now_iso(),))
        conn.commit()

        # Draft follow-ups for any missing docs
        for r in results:
            if r.get("client_id"):
                NotificationService.draft_followup_and_reminders(conn, r["client_id"])

        conn.commit()

        summary_msg = f"Successfully ingested {len(results)} onboarding emails (GST/ITR/Audit)."
        if skipped_count > 0:
            summary_msg += f" Filtered out {skipped_count} unrelated emails."

        return {
            "ok": True,
            "processed": len(results),
            "skipped": skipped_count,
            "message": summary_msg,
            "results": results
        }
