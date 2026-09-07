"""
donors/forms.py

ModelForms for Donor/Donation CRUD, Donor self-submission, and Admin verification.
All widgets apply Bootstrap 5 classes.

Phase 3 additions:
  DonationSubmissionForm  — Donor-facing, includes receipt upload
  DonationVerifyForm      — Admin-only approve/reject form
"""

from django import forms
from .models import Donor, Donation


# ── Staff: Create/Edit Donor profile ──────────────────────────────────────────

class DonorForm(forms.ModelForm):
    class Meta:
        model  = Donor
        fields = ['full_name', 'email', 'phone', 'address', 'notes']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'e.g. Amara Okafor',
                'id': 'id_donor_full_name',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control', 'placeholder': 'donor@example.com',
                'id': 'id_donor_email',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': '+234 800 000 0000',
                'id': 'id_donor_phone',
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Street, City, State',
                'id': 'id_donor_address',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 3,
                'placeholder': 'Internal notes (not shown to donors)',
                'id': 'id_donor_notes',
            }),
        }
        labels = {
            'full_name': 'Full Name',
            'email':     'Email Address',
            'phone':     'Phone Number',
            'address':   'Address',
            'notes':     'Internal Notes',
        }


# ── Staff: Record Donation (admin/member entry) ───────────────────────────────

class DonationForm(forms.ModelForm):
    class Meta:
        model  = Donation
        fields = ['donor', 'amount', 'date', 'payment_method', 'reference_number', 'notes']
        widgets = {
            'donor': forms.Select(attrs={
                'class': 'form-select', 'id': 'id_donation_donor',
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control', 'placeholder': '0.00',
                'step': '0.01', 'min': '0',
                'id': 'id_donation_amount',
            }),
            'date': forms.DateInput(attrs={
                'class': 'form-control', 'type': 'date',
                'id': 'id_donation_date',
            }),
            'payment_method': forms.Select(attrs={
                'class': 'form-select', 'id': 'id_donation_payment_method',
            }),
            'reference_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Transaction ID / Teller No. / Cheque No.',
                'id': 'id_donation_reference',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 2,
                'placeholder': 'Optional notes about this donation',
                'id': 'id_donation_notes',
            }),
        }
        labels = {
            'donor':            'Donor',
            'amount':           'Amount (₦)',
            'date':             'Donation Date',
            'payment_method':   'Payment Method',
            'reference_number': 'Reference / Receipt No.',
            'notes':            'Notes',
        }


# ── Phase 3: Donor self-submission form ───────────────────────────────────────

class DonationSubmissionForm(forms.ModelForm):
    """
    Used by Donor-role users to log their own donation.
    Excludes: donor (set from request.user.donor_profile in the view),
              status (forced to 'pending'), admin fields.
    Includes: receipt (FileField with visual upload styling).
    """

    class Meta:
        model  = Donation
        fields = ['amount', 'date', 'payment_method', 'reference_number', 'receipt', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={
                'class':       'form-control form-control-lg',
                'placeholder': '0.00',
                'step':        '0.01',
                'min':         '1',
                'id':          'id_sub_amount',
            }),
            'date': forms.DateInput(attrs={
                'class': 'form-control',
                'type':  'date',
                'id':    'id_sub_date',
            }),
            'payment_method': forms.Select(attrs={
                'class': 'form-select',
                'id':    'id_sub_payment_method',
            }),
            'reference_number': forms.TextInput(attrs={
                'class':       'form-control',
                'placeholder': 'Bank teller no. / Transaction ID / Cheque no.',
                'id':          'id_sub_reference',
            }),
            'receipt': forms.ClearableFileInput(attrs={
                'class':  'form-control',
                'id':     'id_sub_receipt',
                'accept': '.pdf,.png,.jpg,.jpeg',
            }),
            'notes': forms.Textarea(attrs={
                'class':       'form-control',
                'rows':        2,
                'placeholder': 'Any additional notes about this payment (optional)',
                'id':          'id_sub_notes',
            }),
        }
        labels = {
            'amount':           'Amount Donated (₦)',
            'date':             'Date of Transfer / Payment',
            'payment_method':   'Payment Method',
            'reference_number': 'Reference / Teller No.',
            'receipt':          'Upload Payment Receipt',
            'notes':            'Additional Notes',
        }
        help_texts = {
            'reference_number': 'This helps our team verify your payment quickly.',
            'receipt':          'Upload a PDF scan or photo of your receipt (max 5 MB).',
        }

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= 0:
            raise forms.ValidationError('Amount must be greater than zero.')
        return amount


# ── Phase 3: Admin verification form (approve / reject) ───────────────────────

class DonationVerifyForm(forms.Form):
    """
    Admin-only form for the verify_donation view.

    Two possible actions driven by which submit button the admin presses:
      action='approve' → amount_confirmed is required
      action='reject'  → admin_notes (rejection reason) is required

    Validation is action-aware: clean() checks the action and enforces
    the appropriate field depending on what was clicked.
    """

    ACTION_APPROVE = 'approve'
    ACTION_REJECT  = 'reject'

    action = forms.ChoiceField(
        choices=[
            (ACTION_APPROVE, 'Approve'),
            (ACTION_REJECT,  'Reject'),
        ],
        widget=forms.HiddenInput(),
    )

    amount_confirmed = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'class':       'form-control',
            'placeholder': '0.00',
            'step':        '0.01',
            'min':         '0.01',
            'id':          'id_verify_amount_confirmed',
        }),
        label='Confirmed Amount (₦)',
        help_text='Enter the exact amount that hit the bank account.',
    )

    admin_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class':       'form-control',
            'rows':        2,
            'placeholder': 'Explain why this donation is being rejected...',
            'id':          'id_verify_admin_notes',
        }),
        label='Rejection Reason',
        help_text='This message will be sent to the donor via email.',
    )

    def clean(self):
        cleaned = super().clean()
        action  = cleaned.get('action')

        if action == self.ACTION_APPROVE:
            confirmed = cleaned.get('amount_confirmed')
            if not confirmed:
                self.add_error(
                    'amount_confirmed',
                    'You must enter the confirmed amount to approve this donation.'
                )
            elif confirmed <= 0:
                self.add_error(
                    'amount_confirmed',
                    'Confirmed amount must be greater than zero.'
                )

        elif action == self.ACTION_REJECT:
            notes = cleaned.get('admin_notes', '').strip()
            if not notes:
                self.add_error(
                    'admin_notes',
                    'Please provide a rejection reason — it will be emailed to the donor.'
                )

        return cleaned
