import httpx
import logging
from app.core.config import settings
from app.email.base import EmailProvider

logger = logging.getLogger(__name__)

class BrevoProvider(EmailProvider):
    def send(self, to_email: str, subject: str, html_content: str) -> bool:
        """
        Sends email via Brevo REST API v3.
        Includes improved payload and detailed error logging.
        """
        if not settings.BREVO_SMTP_PASS:
            logger.warning("BREVO_API: Missing API Key (BREVO_SMTP_PASS).")
            return False

        url = "https://api.brevo.com/v3/smtp/email"
        
        # Sender: MUST be verified in Brevo Dashboard -> Senders & IPs
        from_email = settings.EMAILS_FROM_EMAIL or "majeed74905@gmail.com"
        from_name = settings.EMAILS_FROM_NAME or "Zara AI Security"

        # Create a plain text version by removing HTML (basic)
        import re
        text_content = re.sub('<[^<]+?>', '', html_content)

        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "api-key": settings.BREVO_SMTP_PASS
        }

        payload = {
            "sender": {"name": from_name, "email": from_email},
            "to": [{"email": to_email}],
            "subject": subject,
            "htmlContent": html_content,
            "textContent": text_content.strip(),
            "replyTo": {"email": from_email, "name": from_name}
        }

        try:
            logger.info(f"BREVO_API: Sending to {to_email} from {from_email}...")
            
            with httpx.Client() as client:
                response = client.post(url, headers=headers, json=payload, timeout=20)
            
            resp_data = response.json() if response.text else {}
            
            if response.status_code in [200, 201, 202]:
                logger.info(f"BREVO_API: SUCCESS - Message ID: {resp_data.get('messageId')}")
                return True
            else:
                logger.error(f"BREVO_API: FAILED ({response.status_code}) - {response.text}")
                # Log a specific hint if it's a sender issue
                if "sender" in response.text.lower():
                    logger.error(f"BREVO_API: HINT - Ensure '{from_email}' is verified in Brevo Senders.")
                return False
                
        except Exception as e:
            logger.error(f"BREVO_API: CRITICAL EXCEPTION - {str(e)}")
            return False
