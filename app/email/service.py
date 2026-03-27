from typing import Optional, List
from app.email.resend_provider import ResendProvider
from app.email.brevo_provider import BrevoProvider
import logging
import os
import re
from app.core.config import settings

logger = logging.getLogger(__name__)

# Global storage for debugging emails in local development
_last_sent_emails = []

class EmailService:
    def __init__(self):
        self.resend = ResendProvider()
        self.brevo = BrevoProvider()
        self.frontend_url = settings.FRONTEND_URL.rstrip('/')
        self.is_local = "localhost" in settings.FRONTEND_URL or "127.0.0.1" in settings.FRONTEND_URL

    def _send_critical(self, to_email: str, subject: str, html_content: str) -> bool:
        """
        Sends critical emails with absolute fallback.
        """
        logger.info(f"EMAIL_SERVICE: Processing request for {to_email}")
        
        # 1. ALWAYS store and log to console first (DEVELOPMENT SAFETY)
        self._log_and_store(to_email, subject, html_content)

        # 2. Try Resend (Reliable for owner email)
        if self.resend.send(to_email, subject, html_content):
            return True
            
        # 3. Try Brevo Fallback (For all other users)
        logger.warning(f"EMAIL_SERVICE: Resend restricted. Falling back to Brevo for {to_email}")
        if self.brevo.send(to_email, subject, html_content):
            return True
        
        logger.critical(f"EMAIL_SERVICE: PROVIDER FAILURE for {to_email}")
        return self.is_local # Local dev is always true if console log worked

    def _log_and_store(self, to_email: str, subject: str, html_content: str):
        """Prints a high-visibility box to the terminal and stores the email."""
        links = re.findall(r'href="(http[^"]+)"', html_content)
        
        # Store in global list for the debugging endpoint
        _last_sent_emails.append({
            "to": to_email,
            "subject": subject,
            "links": links,
            "html": html_content
        })
        if len(_last_sent_emails) > 10:
            _last_sent_emails.pop(0)

        # Print to terminal
        print("\n" + "╔" + "═"*75 + "╗")
        print("║" + " "*30 + "ZARA AI AUTH EMAIL" + " "*27 + "║")
        print("╠" + "═"*75 + "╣")
        print(f"║ TO:      {to_email:<64} ║")
        print(f"║ SUBJECT: {subject:<64} ║")
        print("╟" + "─"*75 + "╢")
        if links:
            print("║ VERIFICATION / MAGIC LINK:                                                ║")
            for link in links:
                print(f"║ > {link:<71} ║")
        else:
            print("║ [No Links Found]                                                          ║")
        print("╚" + "═"*75 + "╝" + "\n")

    def get_last_emails(self):
        return _last_sent_emails

    def send_verification_email_link(self, email: str, token: str):
        verify_link = f"{self.frontend_url}/verify-email?token={token}"
        subject = "Action Required: Verify your Zara AI Account"
        html_content = self._get_auth_template("Verify Email Address", verify_link, "Please verify your email address to activate your account:")
        return self._send_critical(email, subject, html_content)

    def send_reset_password_email(self, email: str, token: str):
        reset_link = f"{self.frontend_url}/reset-password?token={token}"
        subject = "Reset your Zara AI Password"
        html_content = self._get_auth_template("Reset Password", reset_link, "We received a request to reset your password. Click below:")
        return self._send_critical(email, subject, html_content)

    def send_magic_link(self, email: str, token: str):
        magic_link = f"{self.frontend_url}/auth/magic-link?token={token}"
        subject = "Your Magic Login Link - Zara AI"
        html_content = self._get_auth_template("Login to Zara AI", magic_link, "Click below to instantly sign in:", color="#059669")
        return self._send_critical(email, subject, html_content)

    def _get_auth_template(self, action_text: str, link: str, message: str, color: str = "#7c3aed"):
        return f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: sans-serif; color: #1f2937; line-height: 1.5; background-color: #f9fafb; padding: 40px 0;">
            <div style="max-width: 500px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <div style="background-color: {color}; padding: 24px; text-align: center; color: white;">
                    <h1 style="margin: 0; font-size: 24px;">Zara AI</h1>
                </div>
                <div style="padding: 32px;">
                    <p>{message}</p>
                    <div style="text-align: center; margin: 32px 0;">
                        <a href="{link}" style="background-color: {color}; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; display: inline-block;">
                            {action_text}
                        </a>
                    </div>
                    <p style="font-size: 14px; color: #6b7280;">Secure Link: <br/><a href="{link}">{link}</a></p>
                </div>
            </div>
        </body>
        </html>
        """

    def _send_notification(self, to_email: str, subject: str, html_content: str) -> bool:
        """Sends non-critical emails via Brevo."""
        self._log_and_store(to_email, subject, html_content)
        return self.brevo.send(to_email, subject, html_content)

    def send_welcome_email(self, email: str, name: str):
        subject = "Welcome to Zara AI! 🚀"
        html_content = f"<h1>Welcome, {name}!</h1>"
        return self._send_notification(email, subject, html_content)

    def send_login_alert(self, email: str, ip: str = "Unknown"):
        subject = "New Login Alert - Zara AI"
        html_content = f"<p>New login for {email} from IP {ip}.</p>"
        return self._send_notification(email, subject, html_content)

email_service = EmailService()
