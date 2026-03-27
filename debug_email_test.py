import logging
import sys
import os
from app.core.config import settings
from app.email.resend_provider import ResendProvider
from app.email.brevo_provider import BrevoProvider

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_email_providers():
    test_email = "majeed74905@gmail.com"  # Using the likely admin email
    print(f"--- Starting Email Diagnostics for {test_email} ---")
    print(f"Resend Key Present: {bool(settings.RESEND_API_KEY)}")
    print(f"Brevo User: {settings.BREVO_SMTP_USER}")
    
    # 1. Test Resend
    print("\n[1] Testing Resend API...")
    try:
        resend_provider = ResendProvider()
        success = resend_provider.send(
            test_email, 
            "Resend Test", 
            "<p>This is a test from Resend.</p>"
        )
        print(f"Resend Result: {'SUCCESS' if success else 'FAILED'}")
    except Exception as e:
        print(f"Resend Exception: {e}")

    # 2. Test Brevo
    print("\n[2] Testing Brevo SMTP...")
    try:
        brevo_provider = BrevoProvider()
        success = brevo_provider.send(
            test_email, 
            "Brevo Test", 
            "<p>This is a test from Brevo.</p>"
        )
        print(f"Brevo Result: {'SUCCESS' if success else 'FAILED'}")
    except Exception as e:
        print(f"Brevo Exception: {e}")

if __name__ == "__main__":
    test_email_providers()
