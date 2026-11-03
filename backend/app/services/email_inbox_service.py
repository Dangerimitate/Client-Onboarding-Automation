import os
import re
import email
from email.header import decode_header
import imaplib
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from ..utils import now_iso

class EmailInboxService:
    """
    Production-ready direct IMAP Email Inbox service for live client onboarding.
    Supports Gmail, Outlook 365, Zoho, Yahoo, and Custom IMAP servers.
    """

    PRESETS = {
        "gmail": {
            "name": "Google Workspace / Gmail",
            "host": "imap.gmail.com",
            "port": 993,
            "use_ssl": True,
            "folder": "INBOX",
            "note": "Requires 2FA & App Password (myaccount.google.com/apppasswords)"
        },
        "outlook": {
            "name": "Microsoft 365 / Outlook",
            "host": "outlook.office365.com",
            "port": 993,
            "use_ssl": True,
            "folder": "INBOX",
            "note": "Requires Modern Authentication / App Password"
        },
        "zoho": {
            "name": "Zoho Mail",
            "host": "imappro.zoho.in",
            "port": 993,
            "use_ssl": True,
            "folder": "INBOX",
            "note": "Use imappro.zoho.in (India) or imap.zoho.com (Global)"
        },
        "custom": {
            "name": "Custom IMAP Server",
            "host": "",
            "port": 993,
            "use_ssl": True,
            "folder": "INBOX",
            "note": "Enter your corporate firm mail host and credentials"
        }
    }

    @classmethod
    def get_settings(cls, conn) -> Dict[str, Any]:
        row = conn.execute("SELECT * FROM inbox_settings WHERE id = 1").fetchone()
        if not row:
            # Default empty settings
            return {
                "configured": False,
                "provider": "gmail",
                "host": "imap.gmail.com",
                "port": 993,
                "username": "",
                "password_set": False,
                "use_ssl": True,
                "folder": "INBOX",
                "last_synced": None
            }
        item = dict(row)
        return {
            "configured": bool(item.get("host") and item.get("username")),
            "provider": item.get("provider", "custom"),
            "host": item.get("host", ""),
            "port": item.get("port", 993),
            "username": item.get("username", ""),
            "password_set": bool(item.get("password")),
            "use_ssl": bool(item.get("use_ssl", 1)),
            "folder": item.get("folder", "INBOX"),
            "last_synced": item.get("last_synced")
        }

    @classmethod
    def save_settings(cls, conn, data: Dict[str, Any]):
        provider = data.get("provider", "custom")
        host = data.get("host", "").strip()
        port = int(data.get("port", 993))
        username = data.get("username", "").strip()
        password = data.get("password", "")
        use_ssl = 1 if data.get("use_ssl", True) else 0
        folder = data.get("folder", "INBOX").strip() or "INBOX"

        existing = conn.execute("SELECT password FROM inbox_settings WHERE id = 1").fetchone()
        # If password is empty in update, keep existing password
        if not password and existing and existing["password"]:
            password = existing["password"]

        conn.execute("""
            INSERT INTO inbox_settings (id, provider, host, port, username, password, use_ssl, folder, updated_at)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                provider=excluded.provider,
                host=excluded.host,
                port=excluded.port,
                username=excluded.username,
                password=excluded.password,
                use_ssl=excluded.use_ssl,
                folder=excluded.folder,
                updated_at=excluded.updated_at
        """, (provider, host, port, username, password, use_ssl, folder, now_iso()))
        conn.commit()

    @classmethod
    def test_connection(cls, host: str, port: int, username: str, password: str, use_ssl: bool = True, folder: str = "INBOX") -> Dict[str, Any]:
        """Tests live IMAP connection credentials without saving."""
        if not host or not username or not password:
            return {"ok": False, "error": "Host, username/email, and password are required."}

        mail = None
        try:
            if use_ssl:
                mail = imaplib.IMAP4_SSL(host, port, timeout=10)
            else:
                mail = imaplib.IMAP4(host, port, timeout=10)

            mail.login(username, password)
            status, counts = mail.select(folder, readonly=True)
            if status != "OK":
                return {"ok": False, "error": f"Connected, but failed to select folder '{folder}'. Check folder name."}

            msg_count = int(counts[0].decode() if isinstance(counts[0], bytes) else counts[0] or 0)
            mail.logout()
            return {
                "ok": True,
                "message": f"Successfully authenticated with {host}! Connected to '{folder}' ({msg_count} total messages)."
            }
        except imaplib.IMAP4.error as e:
            return {"ok": False, "error": f"IMAP Authentication failed: {str(e)}"}
        except Exception as e:
            return {"ok": False, "error": f"Connection error: {str(e)}"}
        finally:
            if mail:
                try: mail.logout()
                except Exception: pass

    @classmethod
    def decode_mime_words(cls, s: Optional[str]) -> str:
        """Decode MIME encoded words in email headers (e.g. =?UTF-8?B?...?=)."""
        if not s:
            return ""
        parts = decode_header(s)
        decoded = []
        for content, encoding in parts:
            if isinstance(content, bytes):
                encoding = encoding or 'utf-8'
                try:
                    decoded.append(content.decode(encoding, errors='replace'))
                except Exception:
                    decoded.append(content.decode('latin-1', errors='replace'))
            else:
                decoded.append(str(content))
        return "".join(decoded)

    @classmethod
    def match_service_intent(cls, subject: str, body: str, attachments: Optional[List[Dict]] = None) -> Optional[str]:
        """
        Strict service filter: Matches incoming emails explicitly requesting
        GST, ITR, or Audit onboarding services or submitting required documents.
        Prioritizes explicit client message intent in body/subject over attachment filenames.
        Returns: 'GST', 'ITR', 'Audit', or None.
        """
        # 1. First priority: Check direct email subject & body text written by client
        header_text = re.sub(r'[_.\-/]', ' ', f"{subject or ''}\n{body or ''}")

        if re.search(r'\b(itr|itr1|itr2|itr3|itr4|income\s*tax|tax\s*return|tax\s*filing|form\s*16|form\s*26as|salary\s*slip)\b', header_text, re.IGNORECASE):
            return "ITR"
        if re.search(r'\b(audit|auditing|tax\s*audit|statutory\s*audit|internal\s*audit|financial\s*audit|balance\s*sheet|p&l|profit\s*and\s*loss)\b', header_text, re.IGNORECASE):
            return "Audit"
        if re.search(r'\b(gst|gstin|gstr|gstr1|gstr3b|goods\s+and\s+services?\s+tax)\b', header_text, re.IGNORECASE):
            return "GST"

        # 2. Second priority: Fall back to analyzing attachment filenames if body had no service keywords
        if attachments:
            att_names = re.sub(r'[_.\-/]', ' ', " ".join([a.get("filename", "") for a in attachments if isinstance(a, dict)]))
            if re.search(r'\b(form\s*16|form16|salary|investment|investments|tax\s*saving)\b', att_names, re.IGNORECASE):
                return "ITR"
            if re.search(r'\b(balance\s*sheet|p&l|audit)\b', att_names, re.IGNORECASE):
                return "Audit"
            if re.search(r'\b(gst|gstin|gstr)\b', att_names, re.IGNORECASE):
                return "GST"
            if re.search(r'\b(pan|aadhaar|bank\s*statement)\b', att_names, re.IGNORECASE):
                return "ITR"

        return None

    @classmethod
    def fetch_live_emails(
        cls,
        host: str,
        port: int,
        username: str,
        password: str,
        use_ssl: bool = True,
        folder: str = "INBOX",
        upload_dir: Optional[Path] = None,
        limit: int = 15,
        mark_seen: bool = False,
        conn = None
    ) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """
        Connects to live IMAP server, queries newest client emails, extracts bodies & attachments.
        Returns: (parsed_emails_list, error_message_if_any)
        """
        if not host or not username or not password:
            return [], "Mail server credentials not configured."

        parsed_emails = []
        mail = None
        try:
            if use_ssl:
                mail = imaplib.IMAP4_SSL(host, port, timeout=15)
            else:
                mail = imaplib.IMAP4(host, port, timeout=15)

            mail.login(username, password)
            status, _ = mail.select(folder, readonly=not mark_seen)
            if status != "OK":
                return [], f"Failed to select folder '{folder}'."

            # Fetch the newest 'limit' messages from the mailbox
            status, data = mail.search(None, 'ALL')
            if status != "OK" or not data[0]:
                return [], None

            all_ids = data[0].split()
            # Take the latest 'limit' messages, processing newest first
            msg_ids = all_ids[-limit:] if len(all_ids) > limit else all_ids
            msg_ids.reverse()

            for msg_id in msg_ids:
                status, msg_data = mail.fetch(msg_id, '(RFC822)')
                if status != "OK" or not msg_data:
                    continue

                raw_email = None
                for part in msg_data:
                    if isinstance(part, tuple):
                        raw_email = part[1]
                        break

                if not raw_email:
                    continue

                msg = email.message_from_bytes(raw_email)

                # Sender extraction
                from_header = cls.decode_mime_words(msg.get("From"))
                sender_email = from_header
                sender_name = ""
                m = re.search(r'<([^>]+)>', from_header)
                if m:
                    sender_email = m.group(1).strip()
                    sender_name = re.sub(r'<[^>]+>', '', from_header).strip().strip('"\'')
                else:
                    m = re.search(r'[\w\.-]+@[\w\.-]+', from_header)
                    if m:
                        sender_email = m.group(0)

                subject = cls.decode_mime_words(msg.get("Subject"))
                date_str = msg.get("Date") or now_iso()

                # Body & attachment extraction
                body_parts = []
                attachments = []

                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        content_disposition = str(part.get("Content-Disposition") or "")
                        filename = part.get_filename()

                        if filename:
                            filename = cls.decode_mime_words(filename)

                        # Check if attachment
                        if "attachment" in content_disposition.lower() or filename:
                            if filename and upload_dir:
                                clean_filename = re.sub(r'[^a-zA-Z0-9_\.-]', '_', filename)
                                payload = part.get_payload(decode=True)
                                if payload:
                                    attachments.append({
                                        "filename": clean_filename,
                                        "bytes": payload,
                                        "size": len(payload)
                                    })
                        elif content_type == "text/plain":
                            payload = part.get_payload(decode=True)
                            if payload:
                                try:
                                    body_parts.append(payload.decode('utf-8', errors='replace'))
                                except Exception:
                                    body_parts.append(payload.decode('latin-1', errors='replace'))
                        elif content_type == "text/html" and not body_parts:
                            payload = part.get_payload(decode=True)
                            if payload:
                                html_text = payload.decode('utf-8', errors='replace')
                                plain_text = re.sub(r'<[^>]+>', ' ', html_text)
                                plain_text = re.sub(r'\s+', ' ', plain_text).strip()
                                body_parts.append(plain_text)
                else:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        body_parts.append(payload.decode('utf-8', errors='replace'))

                full_body = "\n".join(body_parts).strip()
                if not full_body:
                    full_body = subject or "Client email with attached documents."

                # Check if sender is an existing client in the database
                existing_service = None
                if conn:
                    client_row = conn.execute("SELECT service FROM clients WHERE email = ?", (sender_email,)).fetchone()
                    if client_row:
                        existing_service = client_row["service"]

                # Service Filter: prioritize explicit service intent from new email message; fall back to existing client service
                detected_service = cls.match_service_intent(subject, full_body, attachments)
                service = detected_service or existing_service
                if not service:
                    # Ignore unrelated marketing/personal emails
                    continue

                parsed_emails.append({
                    "from": sender_email,
                    "sender_name": sender_name,
                    "subject": subject or "(No Subject)",
                    "service": service,
                    "date": date_str,
                    "body": full_body,
                    "attachments": attachments
                })

            return parsed_emails, None

        except Exception as e:
            return [], str(e)
        finally:
            if mail:
                try: mail.logout()
                except Exception: pass
