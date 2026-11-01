import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Tuple, Optional
from ..utils import now_iso

class EmailSenderService:
    """
    Live SMTP Email dispatch service for sending client onboarding follow-ups and reminders.
    Supports Gmail, Outlook 365, Zoho Mail, and custom corporate SMTP hosts.
    """

    @classmethod
    def get_smtp_host_and_port(cls, provider: str, imap_host: str) -> Tuple[str, int, bool]:
        """
        Deduces the SMTP host, port, and TLS requirement based on provider and IMAP configuration.
        """
        provider_lower = (provider or "").lower()
        imap_lower = (imap_host or "").lower()

        # Google / Gmail
        if "gmail" in provider_lower or "gmail.com" in imap_lower:
            return "smtp.gmail.com", 587, True

        # Microsoft 365 / Outlook
        if "outlook" in provider_lower or "office365" in imap_lower:
            return "smtp.office365.com", 587, True

        # Zoho Mail
        if "zoho" in provider_lower or "zoho" in imap_lower:
            if "zoho.in" in imap_lower:
                return "smtppro.zoho.in", 587, True
            return "smtp.zoho.com", 587, True

        # Custom corporate SMTP fallback
        if imap_lower.startswith("imap."):
            smtp_host = "smtp." + imap_lower[5:]
        elif imap_lower.startswith("mail."):
            smtp_host = imap_lower
        else:
            smtp_host = imap_lower or "smtp.gmail.com"

        return smtp_host, 587, True

    @classmethod
    def test_smtp_connection(
        cls,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        use_tls: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """
        Tests active connection and authentication to the SMTP server.
        """
        if not smtp_host or not username or not password:
            return False, "Missing SMTP credentials."

        try:
            if smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=12)
            else:
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=12)
                if use_tls:
                    server.starttls()

            server.login(username, password)
            server.quit()
            return True, None
        except smtplib.SMTPAuthenticationError as e:
            return False, f"SMTP authentication failed: Invalid username or App Password ({e.smtp_error.decode('utf-8', errors='replace') if hasattr(e, 'smtp_error') else e})"
        except Exception as e:
            return False, f"Failed to connect to SMTP server '{smtp_host}:{smtp_port}': {str(e)}"

    @classmethod
    def send_live_email(
        cls,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        to_email: str,
        subject: str,
        body_text: str,
        use_tls: bool = True,
        sender_name: str = "Client Onboarding Team"
    ) -> Tuple[bool, Optional[str]]:
        """
        Sends an email to the client using the firm's configured SMTP server.
        """
        if not to_email:
            return False, "Recipient email address is missing."
        if not username or not password:
            return False, "Firm email credentials not configured in Email Setup."

        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = f"{sender_name} <{username}>"
            msg["To"] = to_email
            msg["Subject"] = subject

            # Plain text version
            part_text = MIMEText(body_text, "plain", "utf-8")
            msg.attach(part_text)

            # Styled HTML version for professional client appearance
            html_content = body_text.replace("\n", "<br>")
            html_body = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
</head>
<body style="margin: 0; padding: 20px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; color: #1e293b;">
    <div style="max-width: 620px; margin: 0 auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 30px; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
        <div style="border-bottom: 2px solid #6366f1; padding-bottom: 12px; margin-bottom: 20px;">
            <h2 style="margin: 0; color: #1e293b; font-size: 18px; font-weight: 700;">CA FIRM & ASSOCIATES</h2>
            <span style="font-size: 12px; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em;">Client Compliance & Onboarding Portal</span>
        </div>
        
        <div style="font-size: 14px; line-height: 1.65; color: #334155;">
            {html_content}
        </div>

        <div style="margin-top: 35px; padding-top: 15px; border-top: 1px solid #f1f5f9; font-size: 12px; color: #94a3b8; text-align: center;">
            <p style="margin: 0;">This email was sent by the <strong>CA Onboard Automation OS</strong> on behalf of {sender_name}.</p>
            <p style="margin: 4px 0 0 0;">Please reply directly with your documents or contact our compliance desk.</p>
        </div>
    </div>
</body>
</html>"""
            part_html = MIMEText(html_body, "html", "utf-8")
            msg.attach(part_html)

            # Establish SMTP connection
            if smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15)
            else:
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
                if use_tls:
                    server.starttls()

            server.login(username, password)
            server.send_message(msg)
            server.quit()
            return True, None

        except smtplib.SMTPAuthenticationError as e:
            err_msg = e.smtp_error.decode('utf-8', errors='replace') if hasattr(e, 'smtp_error') else str(e)
            return False, f"SMTP Authentication failed: {err_msg}. Please check your App Password."
        except Exception as e:
            return False, f"Failed to deliver email via SMTP ({smtp_host}:{smtp_port}): {str(e)}"

