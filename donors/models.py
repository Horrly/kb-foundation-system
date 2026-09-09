"""
donors/models.py

Donor profile and Donation transaction models for the KB Foundation system.
"""

from django.conf import settings
from django.db import models
from django.db.models import Sum, Count
from django.urls import reverse


class Donor(models.Model):
    """
    Represents an individual or organisation that has donated to KB Foundation.

    Phase 1: Linked to a CustomUser account (null/blank for legacy donors
    who don't yet have a portal login).
    """

    # Phase 1: Portal login link
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='donor_profile',
        verbose_name='Portal Login Account',
        help_text=(
            'Link to the CustomUser account for this donor. '
            'Leave blank for donors who do not use the portal.'
        ),
    )

    # ------------------------------------------------------------------ Fields
    full_name = models.CharField(max_length=200, verbose_name='Full Name')
    email     = models.EmailField(unique=True, verbose_name='Email Address')
    phone     = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Phone Number',
        help_text='e.g. +234 801 234 5678',
    )
    address = models.TextField(
        blank=True,
        verbose_name='Address',
        help_text='Street / city / state',
    )
    notes = models.TextField(
        blank=True,
        verbose_name='Internal Notes',
        help_text='Private notes visible only to Admins and Members.',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Date Added')
    updated_at = models.DateTimeField(auto_now=True,     verbose_name='Last Updated')

    # ----------------------------------------------------------------- Methods
    def get_absolute_url(self):
        return reverse('donors:donor_detail', kwargs={'pk': self.pk})

    def total_donated(self):
        """
        Sum of confirmed donations using the admin-verified amount.
        Falls back to the claimed amount if amount_confirmed is not set.
        """
        from django.db.models import Sum, Case, When, F
        result = (
            self.donations
            .filter(status='confirmed')
            .aggregate(
                total=Sum(
                    Case(
                        When(amount_confirmed__isnull=False, then=F('amount_confirmed')),
                        default=F('amount'),
                    )
                )
            )['total']
        )
        return result or 0

    def donation_count(self):
        """Total number of donation submissions (all statuses)."""
        return self.donations.count()

    def confirmed_count(self):
        """Number of confirmed (verified) donations."""
        return self.donations.filter(status='confirmed').count()

    # -------------------------------------------------------------- Dunder / Meta
    def __str__(self):
        return self.full_name

    class Meta:
        verbose_name        = 'Donor'
        verbose_name_plural = 'Donors'
        ordering            = ['-created_at']


# ---------------------------------------------------------------------------

def _donation_receipt_path(instance, filename):
    """Upload path: donation_receipts/<donor_username>/<filename>"""
    import os
    from django.utils.text import slugify
    donor_slug = slugify(instance.donor.full_name) if instance.donor_id else 'unknown'
    ext = os.path.splitext(filename)[1].lower()
    safe_name = f'receipt_{instance.donor_id or "new"}{ext}'
    return f'donation_receipts/{donor_slug}/{safe_name}'


def _validate_receipt_file(value):
    """Accept only PDF, PNG, JPG, JPEG files ≤ 5 MB."""
    import os
    from django.core.exceptions import ValidationError

    allowed_extensions = ['.pdf', '.png', '.jpg', '.jpeg']
    max_size_mb        = 5

    ext = os.path.splitext(value.name)[1].lower()
    if ext not in allowed_extensions:
        raise ValidationError(
            f'Unsupported file type "{ext}". '
            f'Allowed: {", ".join(allowed_extensions)}'
        )
    if value.size > max_size_mb * 1024 * 1024:
        raise ValidationError(
            f'File too large ({value.size / (1024*1024):.1f} MB). '
            f'Maximum size is {max_size_mb} MB.'
        )


class Donation(models.Model):
    """
    A single financial donation linked to a Donor.

    Phase 3: 2-step verification workflow.
      1. Donor submits with status='pending' + receipt upload.
      2. Admin reviews and either confirms (sets amount_confirmed)
         or rejects (sets admin_notes).
    """

    class PaymentMethod(models.TextChoices):
        BANK_TRANSFER = 'bank_transfer', 'Bank Transfer'
        CASH          = 'cash',          'Cash'
        CHEQUE        = 'cheque',        'Cheque'
        ONLINE        = 'online',        'Online Payment'
        MOBILE_MONEY  = 'mobile_money',  'Mobile Money'
        OTHER         = 'other',         'Other'

    class Status(models.TextChoices):
        PENDING       = 'pending',       'Pending'
        CONFIRMED     = 'confirmed',     'Confirmed'
        NOT_CONFIRMED = 'not_confirmed', 'Not Confirmed'

    # ── Core donation fields ─────────────────────────────────────────────────
    donor = models.ForeignKey(
        Donor,
        on_delete=models.CASCADE,
        related_name='donations',
        verbose_name='Donor',
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Amount Claimed (₦)',
        help_text='The amount the donor claims to have sent.',
    )
    date = models.DateField(verbose_name='Donation Date')
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.BANK_TRANSFER,
        verbose_name='Payment Method',
    )
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Reference / Receipt No.',
        help_text='Bank teller number, transaction ID, cheque number, etc.',
    )
    notes = models.TextField(blank=True, verbose_name='Donor Notes')

    # ── Phase 3: Receipt upload ──────────────────────────────────────────────
    receipt = models.FileField(
        upload_to=_donation_receipt_path,
        null=True,
        blank=True,
        validators=[_validate_receipt_file],
        verbose_name='Payment Receipt',
        help_text='Upload a scan or photo of your bank receipt (PDF, PNG, JPG — max 5 MB).',
    )

    # ── Phase 3: Verification fields (Admin-managed) ─────────────────────────
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name='Verification Status',
        db_index=True,
    )
    amount_confirmed = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Amount Confirmed (₦)',
        help_text='The amount the Admin verified actually hit the bank account.',
    )
    admin_note = models.TextField(
        blank=True, 
        null=True,
        verbose_name='Admin Notes',
        help_text='Reason for Not Confirmed or internal verification notes.',
    )

    # ── Timestamps ───────────────────────────────────────────────────────────
    recorded_at  = models.DateTimeField(auto_now_add=True, verbose_name='Submitted At')
    reviewed_at  = models.DateTimeField(null=True, blank=True, verbose_name='Reviewed At')

    # ── Helpers ──────────────────────────────────────────────────────────────
    @property
    def is_pending(self):
        return self.status == self.Status.PENDING

    @property
    def is_confirmed(self):
        return self.status == self.Status.CONFIRMED

    @property
    def is_not_confirmed(self):
        return self.status == self.Status.NOT_CONFIRMED

    @property
    def effective_amount(self):
        """Returns confirmed amount if available, else claimed amount."""
        return self.amount_confirmed if self.amount_confirmed is not None else self.amount

    def __str__(self):
        return (
            f'₦{self.amount:,} from {self.donor.full_name} '
            f'on {self.date} [{self.get_status_display()}]'
        )

    class Meta:
        verbose_name        = 'Donation'
        verbose_name_plural = 'Donations'
        ordering            = ['-date', '-recorded_at']

