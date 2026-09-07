"""
expenditures/forms.py

ModelForm for creating and updating Expenditure records.
Includes client-side and server-side file validation.
"""

from django import forms
from .models import Expenditure, ALLOWED_RECEIPT_EXTENSIONS, MAX_RECEIPT_SIZE_MB


class ExpenditureForm(forms.ModelForm):

    class Meta:
        model  = Expenditure
        fields = ['title', 'category', 'amount', 'date', 'receipt', 'notes']
        widgets = {
            'title': forms.TextInput(attrs={
                'class':       'form-control',
                'placeholder': 'e.g. Venue hire for scholarship ceremony',
                'id':          'id_exp_title',
            }),
            'category': forms.Select(attrs={
                'class': 'form-select',
                'id':    'id_exp_category',
            }),
            'amount': forms.NumberInput(attrs={
                'class':       'form-control',
                'placeholder': '0.00',
                'step':        '0.01',
                'min':         '0',
                'id':          'id_exp_amount',
            }),
            'date': forms.DateInput(attrs={
                'class': 'form-control',
                'type':  'date',
                'id':    'id_exp_date',
            }),
            'receipt': forms.ClearableFileInput(attrs={
                'class':  'form-control',
                'id':     'id_exp_receipt',
                'accept': '.pdf,.jpg,.jpeg,.png',
            }),
            'notes': forms.Textarea(attrs={
                'class':       'form-control',
                'rows':        3,
                'placeholder': 'Optional: additional context or notes',
                'id':          'id_exp_notes',
            }),
        }
        labels = {
            'title':    'Title / Description',
            'category': 'Category',
            'amount':   'Amount (₦)',
            'date':     'Expenditure Date',
            'receipt':  f'Receipt / Proof of Payment (PDF/JPG/PNG, max {MAX_RECEIPT_SIZE_MB} MB)',
            'notes':    'Additional Notes',
        }

    def clean_receipt(self):
        """
        Re-run the model-level validator here so that Django form errors are
        properly attached to the `receipt` field and shown in the template.
        This is belt-and-suspenders validation (model validator also fires on save).
        """
        receipt = self.cleaned_data.get('receipt')
        if receipt and hasattr(receipt, 'name'):
            import os
            ext      = os.path.splitext(receipt.name)[1].lower()
            max_size = MAX_RECEIPT_SIZE_MB * 1024 * 1024

            if ext not in ALLOWED_RECEIPT_EXTENSIONS:
                raise forms.ValidationError(
                    f'Unsupported file type "{ext}". '
                    f'Please upload a PDF, JPG, or PNG.'
                )
            if receipt.size > max_size:
                raise forms.ValidationError(
                    f'File size ({receipt.size / (1024*1024):.1f} MB) exceeds '
                    f'the {MAX_RECEIPT_SIZE_MB} MB limit.'
                )
        return receipt

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= 0:
            raise forms.ValidationError('Amount must be greater than zero.')
        return amount
