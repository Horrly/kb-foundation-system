"""
expenditures/models.py

Expenditure model for tracking KB Foundation spending by category.
"""

import os
from django.db import models
from django.urls import reverse
from django.core.exceptions import ValidationError


# ---------------------------------------------------------------------------
# File upload validators — Risk Note from Build Plan: "15-minute job, don't skip it"
# ---------------------------------------------------------------------------
ALLOWED_RECEIPT_EXTENSIONS = ['.pdf', '.jpg', '.jpeg', '.png']
MAX_RECEIPT_SIZE_MB         = 5  # megabytes


def validate_receipt_file(file):
    """
    Validates that an uploaded receipt:
      1. Has an allowed extension (PDF, JPG, PNG)
      2. Does not exceed MAX_RECEIPT_SIZE_MB
    """
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_RECEIPT_EXTENSIONS:
        raise ValidationError(
            f'Unsupported file type "{ext}". '
            f'Allowed types: {", ".join(ALLOWED_RECEIPT_EXTENSIONS).upper()}.'
        )

    max_bytes = MAX_RECEIPT_SIZE_MB * 1024 * 1024
    if file.size > max_bytes:
        raise ValidationError(
            f'File size ({file.size / (1024*1024):.1f} MB) exceeds the '
            f'{MAX_RECEIPT_SIZE_MB} MB limit. Please compress or split the file.'
        )


def receipt_upload_path(instance, filename):
    """
    Organise uploads into:  media/receipts/<year>/<month>/<filename>
    This prevents one massive flat folder as the project grows.
    """
    from django.utils import timezone
    now = timezone.now()
    return f'receipts/{now.year}/{now.month:02d}/{filename}'


# ---------------------------------------------------------------------------
# Expenditure Model
# ---------------------------------------------------------------------------
class Expenditure(models.Model):
    """
    Records a single expenditure made by the KB Foundation.
    """

    class Category(models.TextChoices):
        SCHOLARSHIP_GRANTS = 'scholarship_grants', 'Scholarship Grants'
        ADMINISTRATIVE     = 'administrative',     'Administrative'
        EVENTS             = 'events',             'Events & Programs'
        MARKETING          = 'marketing',          'Marketing & Outreach'
        LOGISTICS          = 'logistics',          'Logistics & Transport'
        OTHER              = 'other',              'Other'

    # ------------------------------------------------------------------ Fields
    title = models.CharField(
        max_length=255,
        verbose_name='Title / Description',
        help_text='Brief description of what this expenditure was for.',
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Amount (₦)',
    )
    date = models.DateField(verbose_name='Expenditure Date')
    category = models.CharField(
        max_length=30,
        choices=Category.choices,
        default=Category.OTHER,
        verbose_name='Category',
    )
    receipt = models.FileField(
        upload_to=receipt_upload_path,
        blank=True,
        null=True,
        validators=[validate_receipt_file],
        verbose_name='Receipt / Proof of Payment',
        help_text=f'Upload a PDF, JPG, or PNG (max {MAX_RECEIPT_SIZE_MB} MB).',
    )
    notes = models.TextField(
        blank=True,
        verbose_name='Additional Notes',
    )
    recorded_by = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Recorded By',
        help_text='Auto-filled from the logged-in user.',
    )
    created_at  = models.DateTimeField(auto_now_add=True, verbose_name='Created At')
    updated_at  = models.DateTimeField(auto_now=True,     verbose_name='Last Updated')

    # ----------------------------------------------------------------- Methods
    def get_absolute_url(self):
        return reverse('expenditures:expenditure_list')

    def receipt_filename(self):
        """Return just the base filename of the receipt, for display."""
        if self.receipt:
            return os.path.basename(self.receipt.name)
        return None

    def receipt_is_image(self):
        """True if the receipt is a displayable image (JPG/PNG)."""
        if self.receipt:
            ext = os.path.splitext(self.receipt.name)[1].lower()
            return ext in ['.jpg', '.jpeg', '.png']
        return False

    # -------------------------------------------------------------- Dunder / Meta
    def __str__(self):
        return f'{self.title} — ₦{self.amount:,} [{self.get_category_display()}]'

    class Meta:
        verbose_name        = 'Expenditure'
        verbose_name_plural = 'Expenditures'
        ordering            = ['-date', '-created_at']
