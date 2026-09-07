"""
donors/emails.py  — Phase 3

Email notifications for the 2-step donation verification workflow.

  send_incoming_donation_alert  → Notifies Admins & Members of a new submission
  send_donation_confirmed_email → Notifies Donor + Members of approval
  send_donation_rejected_email  → Notifies Donor of rejection with reason
"""

from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model

import logging
logger = logging.getLogger(__name__)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _dispatch(subject: str, body: str, recipients: list[str]):
    """
    Send a single email to a list of recipients.
    Failures are logged but never crash the calling view.
    """
    if not recipients:
        return
    try:
        send_mail(
            subject        = subject,
            message        = body,
            from_email     = settings.DEFAULT_FROM_EMAIL,
            recipient_list = recipients,
            fail_silently  = False,
        )
    except Exception as exc:
        logger.error('Email dispatch failed (subject="%s"): %s', subject, exc)


def _staff_emails(*roles):
    """
    Return a list of email addresses for all active users matching the given roles.
    Avoids importing CustomUser directly (uses get_user_model()).
    """
    UserModel = get_user_model()
    return list(
        UserModel.objects
        .filter(role__in=roles, is_active=True)
        .exclude(email='')
        .values_list('email', flat=True)
    )


# ── Notification: Incoming donation submitted by Donor ────────────────────────

def send_incoming_donation_alert(donation, review_url: str):
    """
    Fired immediately when a Donor submits a new donation.
    Recipients: all Admins and Members.

    Contains donor name, claimed amount, payment method, reference number,
    and a direct link to the pending-donations queue.
    """
    subject = f'[ACTION REQUIRED] Incoming Donation of \u20a6{donation.amount:,} — Pending Verification'

    body = f"""Hello,

A new donation has been submitted and is awaiting verification.

  Donor Name     : {donation.donor.full_name}
  Donor Email    : {donation.donor.email}
  Claimed Amount : \u20a6{donation.amount:,}
  Payment Method : {donation.get_payment_method_display()}
  Reference No.  : {donation.reference_number or 'Not provided'}
  Submitted At   : {donation.recorded_at.strftime('%d %b %Y, %H:%M') if donation.recorded_at else 'N/A'}
  Receipt        : {'Uploaded' if donation.receipt else 'Not uploaded'}

Please review and verify this donation at:
{review_url}

Once verified, the donor will be automatically notified by email.

— KB Foundation System
{settings.DEFAULT_FROM_EMAIL}
"""
    recipients = _staff_emails('admin', 'member')
    _dispatch(subject, body, recipients)


# ── Notification: Donation confirmed by Admin ─────────────────────────────────

def send_donation_confirmed_email(donation, donor_user=None):
    """
    Fired when an Admin confirms a donation.

    Recipients:
      - The Donor (if they have a portal login with email)
      - All Members (for their records)
    """
    subject = f'Payment Confirmed — \u20a6{donation.amount_confirmed or donation.amount:,} — KB Foundation'

    body = f"""Hello {donation.donor.full_name},

Great news! Your donation to the KB Foundation has been verified and confirmed.

  Reference No.    : {donation.reference_number or 'N/A'}
  Claimed Amount   : \u20a6{donation.amount:,}
  Confirmed Amount : \u20a6{donation.amount_confirmed or donation.amount:,}
  Payment Method   : {donation.get_payment_method_display()}
  Donation Date    : {donation.date.strftime('%d %b %Y')}
  Status           : CONFIRMED

Thank you sincerely for your generous support of the KB Foundation.
Your contribution directly funds scholarships for deserving students
across Nigeria.

With warm gratitude,
The KB Foundation Team
{settings.DEFAULT_FROM_EMAIL}
"""

    recipients = []
    # Notify the donor if they have a linked user account with email
    if donor_user and donor_user.email:
        recipients.append(donor_user.email)
    elif donation.donor.email:
        recipients.append(donation.donor.email)

    # CC all Members
    recipients += _staff_emails('member')
    # Deduplicate
    recipients = list(dict.fromkeys(recipients))

    _dispatch(subject, body, recipients)


# ── Notification: Donation rejected by Admin ──────────────────────────────────

def send_donation_rejected_email(donation, donor_user=None):
    """
    Fired when an Admin rejects a donation.
    Recipient: the Donor only (with the admin_notes as reason).
    """
    subject = 'Payment Could Not Be Verified — KB Foundation'

    body = f"""Hello {donation.donor.full_name},

We regret to inform you that we were unable to verify your recent donation
to the KB Foundation.

  Reference No.  : {donation.reference_number or 'N/A'}
  Claimed Amount : \u20a6{donation.amount:,}
  Payment Method : {donation.get_payment_method_display()}
  Donation Date  : {donation.date.strftime('%d %b %Y')}

Reason:
  {donation.admin_notes or 'Amount does not tally with receipt. Please contact Admin.'}

This may be due to:
  - A mismatch between the claimed amount and the amount received
  - An unclear or unreadable receipt
  - A missing or incorrect reference number

Please contact the KB Foundation office or your assigned Admin to resolve
this issue. You may also resubmit a corrected donation with the right
reference and receipt.

We apologise for any inconvenience.

The KB Foundation Team
{settings.DEFAULT_FROM_EMAIL}
"""

    recipient = None
    if donor_user and donor_user.email:
        recipient = donor_user.email
    elif donation.donor.email:
        recipient = donation.donor.email

    if recipient:
        _dispatch(subject, body, [recipient])
