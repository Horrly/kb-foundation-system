"""
scholarships/forms.py  (updated for Day 11 — ReviewForm added)
"""

import os
from django import forms
from .models import (
    ScholarshipApplication, Document, ScholarshipRecipient,
    ALLOWED_DOC_EXTENSIONS, MAX_DOC_SIZE_MB,
)

LEVEL_CHOICES = [
    ('', 'Select your current level'),
    ('100 Level', '100 Level'),
    ('200 Level', '200 Level'),
    ('300 Level', '300 Level'),
    ('400 Level', '400 Level'),
    ('500 Level', '500 Level (Law/Medicine extra year)'),
    ('MSc Year 1', "Postgraduate — MSc Year 1"),
    ('MSc Year 2', "Postgraduate — MSc Year 2"),
    ('PhD',        "Postgraduate — PhD"),
]


# ── ApplicationForm ───────────────────────────────────────────────────────────

class ApplicationForm(forms.ModelForm):
    class Meta:
        model  = ScholarshipApplication
        fields = [
            'academic_session', 'institution', 'course_of_study',
            'level', 'current_cgpa', 'statement_of_purpose',
        ]
        widgets = {
            'academic_session': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. 2024/2025',
                'id': 'id_app_session',
            }),
            'institution': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'University / Polytechnic / College name',
                'id': 'id_app_institution',
            }),
            'course_of_study': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Computer Science, Medicine, Law',
                'id': 'id_app_course',
            }),
            'level': forms.Select(
                choices=LEVEL_CHOICES,
                attrs={'class': 'form-select', 'id': 'id_app_level'},
            ),
            'current_cgpa': forms.NumberInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. 4.50',
                'step': '0.01', 'min': '0', 'max': '5',
                'id': 'id_app_cgpa',
            }),
            'statement_of_purpose': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 6,
                'placeholder': (
                    'Tell us about yourself, your academic achievements, '
                    'your financial situation, and your career goals. '
                    'Minimum 50 words recommended.'
                ),
                'id': 'id_app_statement',
            }),
        }
        labels = {
            'academic_session':     'Academic Session',
            'institution':          'Institution Name',
            'course_of_study':      'Course of Study / Programme',
            'level':                'Current Academic Level',
            'current_cgpa':         'Current CGPA / GPA',
            'statement_of_purpose': 'Statement of Purpose',
        }

    def clean_current_cgpa(self):
        cgpa = self.cleaned_data.get('current_cgpa')
        if cgpa is not None and (cgpa < 0 or cgpa > 5):
            raise forms.ValidationError(
                'CGPA must be between 0.00 and 5.00.'
            )
        return cgpa

    def clean_statement_of_purpose(self):
        statement  = self.cleaned_data.get('statement_of_purpose', '')
        word_count = len(statement.split())
        if word_count < 50:
            raise forms.ValidationError(
                f'Your statement has {word_count} word(s). '
                'Please write at least 50 words.'
            )
        return statement


# ── DocumentForm ─────────────────────────────────────────────────────────────

class DocumentForm(forms.ModelForm):
    class Meta:
        model  = Document
        fields = ['document_type', 'file']
        widgets = {
            'document_type': forms.Select(attrs={
                'class': 'form-select', 'id': 'id_doc_type',
            }),
            'file': forms.ClearableFileInput(attrs={
                'class': 'form-control', 'id': 'id_doc_file',
                'accept': '.pdf,.jpg,.jpeg,.png',
            }),
        }
        labels = {
            'document_type': 'Document Type',
            'file': f'Upload File (PDF / JPG / PNG — max {MAX_DOC_SIZE_MB} MB)',
        }

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file and hasattr(file, 'name'):
            ext      = os.path.splitext(file.name)[1].lower()
            max_size = MAX_DOC_SIZE_MB * 1024 * 1024
            if ext not in ALLOWED_DOC_EXTENSIONS:
                raise forms.ValidationError(
                    f'Unsupported file type "{ext}". '
                    'Please upload a PDF, JPG, or PNG.'
                )
            if file.size > max_size:
                raise forms.ValidationError(
                    f'File is too large ({file.size / (1024*1024):.1f} MB). '
                    f'Maximum allowed size is {MAX_DOC_SIZE_MB} MB.'
                )
        return file


# ── ReviewForm (Day 11) ───────────────────────────────────────────────────────

class ReviewForm(forms.ModelForm):
    """
    Used by Admins / Members / Reviewers to update an application's
    status and add internal reviewer notes.
    """
    class Meta:
        model  = ScholarshipApplication
        fields = ['status', 'reviewer_notes']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'form-select form-select-lg fw-semibold',
                'id':    'id_review_status',
            }),
            'reviewer_notes': forms.Textarea(attrs={
                'class':       'form-control',
                'rows':        4,
                'placeholder': 'Add your review notes here. These are internal and not shown to the applicant '
                               'unless the application is rejected.',
                'id':          'id_review_notes',
            }),
        }
        labels = {
            'status':         'Update Application Status',
            'reviewer_notes': 'Reviewer Notes (Internal)',
        }


# ── AwardForm (Day 11) ───────────────────────────────────────────────────────

class AwardForm(forms.ModelForm):
    """
    Filled by Admin to record the scholarship award amount
    when approving an application.
    """
    class Meta:
        model  = ScholarshipRecipient
        fields = ['awarded_date', 'amount_awarded', 'notes']
        widgets = {
            'awarded_date': forms.DateInput(attrs={
                'class': 'form-control', 'type': 'date',
                'id':    'id_award_date',
            }),
            'amount_awarded': forms.NumberInput(attrs={
                'class': 'form-control', 'placeholder': '0.00',
                'step': '0.01', 'min': '0',
                'id':   'id_award_amount',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 2,
                'placeholder': 'Any special conditions or notes for this award',
                'id':   'id_award_notes',
            }),
        }
        labels = {
            'awarded_date':   'Award Date',
            'amount_awarded': 'Amount Awarded (₦)',
            'notes':          'Award Notes',
        }

    def clean_amount_awarded(self):
        amount = self.cleaned_data.get('amount_awarded')
        if amount is not None and amount <= 0:
            raise forms.ValidationError('Award amount must be greater than zero.')
        return amount
