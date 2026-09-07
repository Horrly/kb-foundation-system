"""
accounts/forms.py

Authentication, self-registration, and admin onboarding forms
for the KB Foundation system.
"""

from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from .models import CustomUser


# ── Login Forms (Phase 4: split portals) ─────────────────────────────────────

class CustomLoginForm(AuthenticationForm):
    """
    Base login form — works with EmailOrUniqueIdModelBackend (Phase 2.5).
    Subclassed into StandardLoginForm and StaffDonorLoginForm for the
    split-portal UX introduced in Phase 4.
    """

    username = forms.CharField(
        label='Email, Username, or Unique ID',
        max_length=254,
        widget=forms.TextInput(attrs={
            'class':       'form-control form-control-lg',
            'placeholder': 'Email, username, or Unique ID (e.g. KBD-0001)',
            'autofocus':   True,
            'id':          'id_login_username',
        }),
    )

    password = forms.CharField(
        label='Password',
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class':       'form-control form-control-lg',
            'placeholder': 'Enter your password',
            'id':          'id_login_password',
        }),
    )

    remember_me = forms.BooleanField(
        required=False,
        label='Keep me logged in',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id':    'id_remember_me',
        }),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].help_text = ''


class StandardLoginForm(CustomLoginForm):
    """
    Phase 4: Standard portal login (Applicants & Admins).
    Credential field labelled as 'Email Address' — most users on this
    portal log in by email rather than a unique ID.
    """

    username = forms.CharField(
        label='Email Address',
        max_length=254,
        widget=forms.TextInput(attrs={
            'class':       'form-control form-control-lg',
            'placeholder': 'Enter your email address',
            'autofocus':   True,
            'autocomplete':'email',
            'id':          'id_login_username',
            'inputmode':   'email',
        }),
    )

    password = forms.CharField(
        label='Password',
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class':       'form-control form-control-lg',
            'placeholder': 'Enter your password',
            'id':          'id_login_password',
        }),
    )

    remember_me = forms.BooleanField(
        required=False,
        label='Keep me logged in',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id':    'id_remember_me',
        }),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].help_text = ''

    def clean(self):
        cleaned_data = super().clean()
        user = self.get_user()
        if user:
            from accounts.models import CustomUser
            if user.role in [CustomUser.Role.DONOR, CustomUser.Role.MEMBER, CustomUser.Role.REVIEWER]:
                raise forms.ValidationError("Please use the Staff & Donor Portal to log in.")
        return cleaned_data


class StaffDonorLoginForm(CustomLoginForm):
    """
    Phase 4: Staff & Donor portal login (Members, Reviewers & Donors).
    Credential field labelled as 'Unique ID' — portal users receive
    a reference ID (KBD-0001, KBM-0003, etc.) and use it to log in.
    Also accepts email as a fallback via the backend.
    """

    username = forms.CharField(
        label='Unique ID',
        max_length=254,
        widget=forms.TextInput(attrs={
            'class':       'form-control form-control-lg',
            'placeholder': 'Enter your Unique ID (e.g. KBD-0001)',
            'autofocus':   True,
            'autocomplete':'username',
            'id':          'id_login_username',
        }),
    )

    password = forms.CharField(
        label='Password',
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class':       'form-control form-control-lg',
            'placeholder': 'Enter your password',
            'id':          'id_login_password',
        }),
    )

    remember_me = forms.BooleanField(
        required=False,
        label='Keep me logged in',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id':    'id_remember_me',
        }),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].help_text = 'You can also log in with your registered email address.'

    def clean(self):
        cleaned_data = super().clean()
        user = self.get_user()
        if user:
            from accounts.models import CustomUser
            if user.is_superuser or user.role in [CustomUser.Role.APPLICANT, CustomUser.Role.ADMIN]:
                raise forms.ValidationError("Please use the standard Applicant Portal to log in.")
        return cleaned_data


# ── Applicant Self-Registration Form ─────────────────────────────────────────

class ApplicantRegistrationForm(forms.ModelForm):
    """
    Public registration form — always creates an APPLICANT-role user.
    Staff / Donor accounts are provisioned by Admins via the onboarding views.
    """

    password1 = forms.CharField(
        label='Password',
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class':       'form-control',
            'placeholder': 'Create a password',
            'id':          'id_reg_password1',
        }),
        help_text='Minimum 8 characters.',
    )

    password2 = forms.CharField(
        label='Confirm Password',
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class':       'form-control',
            'placeholder': 'Repeat your password',
            'id':          'id_reg_password2',
        }),
    )

    class Meta:
        model  = CustomUser
        fields = ('first_name', 'last_name', 'username', 'email')
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'First name',
                'id': 'id_reg_first_name',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Last name',
                'id': 'id_reg_last_name',
            }),
            'username': forms.TextInput(attrs={
                'class': 'form-control', 'placeholder': 'Choose a username',
                'id': 'id_reg_username',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control', 'placeholder': 'your@email.com',
                'id': 'id_reg_email',
            }),
        }

    def clean_password2(self):
        p1 = self.cleaned_data.get('password1')
        p2 = self.cleaned_data.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError('Passwords do not match.')
        if p1 and len(p1) < 8:
            raise forms.ValidationError('Password must be at least 8 characters.')
        return p2

    def save(self, commit=True):
        user          = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        user.role     = CustomUser.Role.APPLICANT
        if commit:
            user.save()
            from django.contrib.auth.models import Group
            try:
                user.groups.add(Group.objects.get(name='Applicant'))
            except Group.DoesNotExist:
                pass
        return user


# ── Admin Onboarding — Base Form ─────────────────────────────────────────────

class _AdminProvisionBaseForm(forms.ModelForm):
    """
    Internal base form shared by AdminRegisterMemberForm and
    AdminRegisterDonorForm.

    The Admin fills in the user's basic info; the view auto-generates the
    password, sets requires_password_change=True, and dispatches the
    welcome email.
    """

    class Meta:
        model  = CustomUser
        fields = ('first_name', 'last_name', 'email')
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First name',
                'id': 'id_prov_first_name',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last name',
                'id': 'id_prov_last_name',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'user@example.com',
                'id': 'id_prov_email',
            }),
        }
        labels = {
            'first_name': 'First Name',
            'last_name':  'Last Name',
            'email':      'Email Address',
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError(
                'A user with this email address already exists.'
            )
        return email


# ── Admin Onboarding — Member ─────────────────────────────────────────────────

class AdminRegisterMemberForm(_AdminProvisionBaseForm):
    """
    Used by Admin to create a new Member-role user.
    Password is auto-generated in the view — no password fields here.
    """
    pass   # Inherits all fields from base; role set to MEMBER in view


# ── Admin Onboarding — Donor ──────────────────────────────────────────────────

class AdminRegisterDonorForm(_AdminProvisionBaseForm):
    """
    Used by Admin to create a new Donor-role user and matching Donor profile.
    Adds donor-specific profile fields: phone, address, internal notes.
    """

    phone = forms.CharField(
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={
            'class':       'form-control',
            'placeholder': '+234 801 234 5678',
            'id':          'id_prov_phone',
        }),
        label='Phone Number',
    )

    address = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class':   'form-control',
            'rows':    2,
            'placeholder': 'Street / City / State',
            'id':      'id_prov_address',
        }),
        label='Address',
    )

    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class':       'form-control',
            'rows':        2,
            'placeholder': 'Internal notes (not visible to donor)',
            'id':          'id_prov_notes',
        }),
        label='Internal Notes',
    )


# ── Bootstrap-Styled Password Change Form ─────────────────────────────────────

class StyledPasswordChangeForm(PasswordChangeForm):
    """
    Wraps Django's built-in PasswordChangeForm with Bootstrap 5 widget styling.
    Used by ForcePasswordChangeView on first login.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        styles = {
            'old_password':  ('id_old_password',   'Current Password'),
            'new_password1': ('id_new_password1',  'New Password'),
            'new_password2': ('id_new_password2',  'Confirm New Password'),
        }
        for field_name, (field_id, placeholder) in styles.items():
            self.fields[field_name].widget = forms.PasswordInput(attrs={
                'class':       'form-control form-control-lg',
                'placeholder': placeholder,
                'id':          field_id,
                'autocomplete':'new-password',
            })
