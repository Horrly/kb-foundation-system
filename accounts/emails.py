"""
accounts/emails.py

Centralised email dispatch functions for the KB Foundation system.

All emails print to the terminal console in development
(EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend').
Replace with SMTP settings for production.
"""

from django.core.mail import send_mail
from django.conf import settings


# ── Shared helper ─────────────────────────────────────────────────────────────

def _send(subject: str, body: str, recipient_email: str):
    """
    Wrapper around send_mail with consistent FROM address.
    Propagates exceptions so callers can handle and report SMTP errors.
    """
    send_mail(
        subject       = subject,
        message       = body,
        from_email    = settings.DEFAULT_FROM_EMAIL,
        recipient_list= [recipient_email],
        fail_silently = False,
    )



# ── Staff / Donor Account Created (Admin-Provisioned) ─────────────────────────

def send_credentials_email(user, raw_password: str, login_url: str):
    """
    Sent by Admin after creating a Member or Donor account.

    Contents:
      - Greeting and unique_id
      - Auto-generated temporary password
      - Login URL
      - Mandatory first-login password change instruction
    """
    portal_name = "Donor" if user.role == "donor" else "Member"
    subject = f'Welcome to KB Foundation — Your Portal Access ({user.unique_id})'

    body = f"""Hello {user.get_full_name() or user.username},

Welcome to KB Foundation. Your account has been created for the {portal_name} Portal.

Your Unique ID is: {user.unique_id}
Your temporary password is: {raw_password}

Login here: {login_url}

You will be required to change this password upon your first login. Please choose a strong, unique password that you do not use elsewhere.

If you did not expect this email, please contact the KB Foundation office immediately.

With warm regards,
The KB Foundation Team
{settings.DEFAULT_FROM_EMAIL}
"""
    _send(subject, body, user.email)


# ── Applicant Self-Registration Welcome ───────────────────────────────────────

def send_welcome_applicant_email(user, login_url: str):
    """
    Sent immediately after a new applicant self-registers.
    Encourages them to complete their application and upload documents.
    """
    subject = 'Welcome to the KB Foundation Scholarship Portal!'

    body = f"""Hello {user.get_full_name() or user.username},

Thank you for registering with the KB Foundation Scholarship Portal!

Your account has been successfully created. Here are your details:

  Reference ID : {user.unique_id}
  Username     : {user.username}
  Email        : {user.email}

You can now log in and apply for a scholarship at:
{login_url}

What to do next:
  1. Log in to your account
  2. Click "Apply for Scholarship"
  3. Fill in the application form
  4. Upload your supporting documents (admission letter, school ID, result)

Our scholarship committee will review all applications carefully.
Shortlisted applicants will be contacted with further details.

We wish you the very best in your studies!

With warm regards,
The KB Foundation Team
{settings.DEFAULT_FROM_EMAIL}
"""
    _send(subject, body, user.email)
