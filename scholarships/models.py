"""
scholarships/models.py

Three-model scholarship pipeline:
  ScholarshipApplication → Document (many), ScholarshipRecipient (one)
"""

import os
from django.db import models
from django.conf import settings
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.utils import timezone


# ── File validation constants ────────────────────────────────────────────────
ALLOWED_DOC_EXTENSIONS = ['.pdf', '.jpg', '.jpeg', '.png']
MAX_DOC_SIZE_MB        = 5


def validate_document_file(file):
    """
    Dual-layer guard (mirrors expenditures risk mitigation):
      1. Extension whitelist: PDF, JPG, PNG only.
      2. File-size cap: 5 MB.
    """
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in ALLOWED_DOC_EXTENSIONS:
        raise ValidationError(
            f'Unsupported file type "{ext}". '
            f'Please upload a PDF, JPG, or PNG.'
        )
    max_bytes = MAX_DOC_SIZE_MB * 1024 * 1024
    if file.size > max_bytes:
        raise ValidationError(
            f'File size ({file.size / (1024 * 1024):.1f} MB) exceeds the '
            f'{MAX_DOC_SIZE_MB} MB limit.'
        )


def document_upload_path(instance, filename):
    """
    Organise uploads by applicant username:
      media/scholarship_docs/<username>/<document_type>/<filename>
    """
    username   = instance.application.applicant.username
    doc_type   = instance.document_type or 'other'
    return f'scholarship_docs/{username}/{doc_type}/{filename}'


# ── ScholarshipApplication ───────────────────────────────────────────────────

class ScholarshipApplication(models.Model):

    class Status(models.TextChoices):
        PENDING          = 'pending',          'Pending'
        IN_REVIEW        = 'in_review',        'In Review'
        RECOMMENDED      = 'recommended',      'Recommended'
        ACCEPTED         = 'accepted',         'Accepted'
        SCREENING_PASSED = 'screening_passed', 'Screening Passed'
        AWARDED          = 'awarded',          'Awarded'
        DISBURSED        = 'disbursed',        'Disbursed'
        REJECTED         = 'rejected',         'Rejected'

    # Core FK — CASCADE so deleting the user removes their application
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='scholarship_applications',
        verbose_name='Applicant',
    )

    # Academic details
    academic_session  = models.CharField(
        max_length=20,
        verbose_name='Academic Session',
        help_text='e.g. 2024/2025',
    )
    institution       = models.CharField(
        max_length=255,
        verbose_name='Institution / University',
    )
    course_of_study   = models.CharField(
        max_length=255,
        verbose_name='Course of Study',
    )
    level             = models.CharField(
        max_length=50,
        verbose_name='Current Level',
        help_text='e.g. 100 Level, 200 Level, MSc Year 1',
    )
    current_cgpa      = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        verbose_name='Current CGPA / GPA',
        help_text='On a 5.0 or 4.0 scale — specify scale in your statement.',
    )
    statement_of_purpose = models.TextField(
        verbose_name='Statement of Purpose',
        help_text='Explain why you need this scholarship and your academic goals.',
    )

    # Phase 41: New explicit document fields
    school_letter = models.FileField(
        upload_to='scholarship_docs/school_letters/',
        blank=True, null=True,
        validators=[validate_document_file],
        verbose_name='Official School Letter'
    )
    birth_certificate = models.FileField(
        upload_to='scholarship_docs/birth_certs/',
        blank=True, null=True,
        validators=[validate_document_file],
        verbose_name='Birth Certificate'
    )
    passport_photo = models.ImageField(
        upload_to='scholarship_docs/passports/',
        blank=True, null=True,
        verbose_name='Passport Photograph'
    )

    # Phase 45: Scholar Bank Details Module
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    account_number = models.CharField(max_length=20, blank=True, null=True)
    account_name = models.CharField(max_length=150, blank=True, null=True)
    disbursement_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    is_disbursed = models.BooleanField(default=False)

    # Workflow
    status        = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name='Application Status',
        db_index=True,
    )
    reviewer_notes = models.TextField(
        blank=True,
        verbose_name='Reviewer Notes',
        help_text='Internal notes from the reviewer. Not shown to applicant.',
    )
    is_submitted = models.BooleanField(
        default=False,
        verbose_name='Final Submission Locked'
    )
    
    # Phase 42: Two-Tier Review System
    member_recommendation = models.CharField(
        max_length=50,
        choices=[
            ('Pending', 'Pending'),
            ('Recommended', 'Recommended'),
            ('Not Recommended', 'Not Recommended')
        ],
        default='Pending',
        verbose_name='Member Recommendation'
    )

    # Timestamps
    application_date = models.DateField(
        default=timezone.now,
        verbose_name='Application Date',
    )
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    # ── Methods ──────────────────────────────────────────────────────────────
    def get_absolute_url(self):
        return reverse('scholarships:application_status')

    def get_status_badge_class(self):
        """Returns a CSS class string for the status badge."""
        return {
            self.Status.PENDING:      'badge-pending',
            self.Status.IN_REVIEW:    'badge-under-review',
            self.Status.RECOMMENDED:  'badge-info',
            self.Status.ACCEPTED:     'badge-approved',
            self.Status.REJECTED:     'badge-rejected',
        }.get(self.status, 'bg-secondary')

    def is_editable(self):
        """Applicant can only edit while status is still 'pending'."""
        return self.status == self.Status.PENDING

    def __str__(self):
        return (
            f'{self.applicant.get_full_name() or self.applicant.username} — '
            f'{self.academic_session} [{self.get_status_display()}]'
        )

    class Meta:
        verbose_name        = 'Scholarship Application'
        verbose_name_plural = 'Scholarship Applications'
        ordering            = ['-application_date', '-created_at']
        # Prevent duplicate applications for the same session by the same person
        unique_together     = [('applicant', 'academic_session')]


# ── Document ─────────────────────────────────────────────────────────────────

class Document(models.Model):

    class DocumentType(models.TextChoices):
        ADMISSION_LETTER = 'admission_letter', 'Admission / Acceptance Letter'
        SCHOOL_ID        = 'school_id',        'School ID Card'
        RESULT           = 'result',           'Academic Result / Transcript'
        OTHER            = 'other',            'Other Supporting Document'

    application   = models.ForeignKey(
        ScholarshipApplication,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name='Application',
    )
    document_type = models.CharField(
        max_length=30,
        choices=DocumentType.choices,
        default=DocumentType.OTHER,
        verbose_name='Document Type',
    )
    file = models.FileField(
        upload_to=document_upload_path,
        validators=[validate_document_file],
        verbose_name='File',
        help_text=f'PDF, JPG, or PNG — max {MAX_DOC_SIZE_MB} MB.',
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    # ── Helpers ──────────────────────────────────────────────────────────────
    def filename(self):
        return os.path.basename(self.file.name)

    def is_image(self):
        return os.path.splitext(self.file.name)[1].lower() in ['.jpg', '.jpeg', '.png']

    def __str__(self):
        return f'{self.get_document_type_display()} — {self.application}'

    class Meta:
        verbose_name        = 'Document'
        verbose_name_plural = 'Documents'
        ordering            = ['document_type', '-uploaded_at']


# ── ScholarshipRecipient ─────────────────────────────────────────────────────

class ScholarshipRecipient(models.Model):
    """
    Created when a ScholarshipApplication is approved.
    OneToOne ensures one award record per application.
    """
    application = models.OneToOneField(
        ScholarshipApplication,
        on_delete=models.CASCADE,
        related_name='recipient_record',
        verbose_name='Application',
    )
    awarded_date   = models.DateField(verbose_name='Award Date')
    amount_awarded = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name='Amount Awarded (₦)',
    )
    notes = models.TextField(blank=True, verbose_name='Award Notes')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f'{self.application.applicant.get_full_name()} — '
            f'₦{self.amount_awarded:,} on {self.awarded_date}'
        )

    class Meta:
        verbose_name        = 'Scholarship Recipient'
        verbose_name_plural = 'Scholarship Recipients'
        ordering            = ['-awarded_date']
