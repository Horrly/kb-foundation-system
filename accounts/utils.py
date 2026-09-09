from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse

def safe_send_mail(subject, message, recipient_list, html_message=None):
    """
    Helper function to safely attempt sending emails without crashing the app 
    if outbound SMTP is blocked by the hosting provider.
    """
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=False,
        )
    except Exception as e:
        print(f"Email delivery skipped (Network unreachable): {e}")


def send_welcome_applicant_email(user, login_url):
    """
    Sends a welcome email to newly registered applicants safely.
    """
    subject = "Welcome to KB Foundation Scholarship Portal"
    message = (
        f"Hello {user.get_full_name() or user.username},\n\n"
        f"Your applicant account has been successfully created.\n"
        f"You can log in here: {login_url}\n\n"
        f"Thank you for applying!"
    )
    
    # Use safe_send_mail instead of direct send_mail to prevent 500 errors on Render
    safe_send_mail(
        subject=subject,
        message=message,
        recipient_list=[user.email]
    )