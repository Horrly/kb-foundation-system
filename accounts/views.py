"""
accounts/views.py

Authentication, registration, admin onboarding, and password management views.

Phase 2 additions:
  - admin_register_member   — Admin creates a Member account
  - admin_register_donor    — Admin creates a Donor account + Donor profile
  - force_password_change   — First-login forced password change
  - register_view updated   — Now sends welcome email on success
"""

import secrets
import string
import uuid

from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils.safestring import mark_safe

from .decorators import role_required
from .emails import send_credentials_email, send_welcome_applicant_email
from .forms import (
    CustomLoginForm,
    StandardLoginForm,
    StaffDonorLoginForm,
    ApplicantRegistrationForm,
    AdminRegisterMemberForm,
    AdminRegisterDonorForm,
    StyledPasswordChangeForm,
)
from .models import CustomUser


# ── Shared helpers ─────────────────────────────────────────────────────────────

ROLE_DASHBOARD_URL = {
    CustomUser.Role.ADMIN:     'reports:admin_dashboard',
    CustomUser.Role.MEMBER:    'reports:member_dashboard',
    CustomUser.Role.REVIEWER:  'reports:reviewer_dashboard',
    CustomUser.Role.APPLICANT: 'reports:applicant_dashboard',
    CustomUser.Role.DONOR:     'reports:donor_dashboard',
}


def get_dashboard_url(user):
    """Return the named URL for a user's role-specific dashboard."""
    if user.is_superuser or user.is_staff:
        return 'reports:admin_dashboard'
    return ROLE_DASHBOARD_URL.get(user.role, 'reports:applicant_dashboard')


def _generate_password(length: int = 12) -> str:
    """
    Generate a cryptographically secure random password.
    Guarantees at least one uppercase, one lowercase, one digit, one symbol.
    """
    alphabet = string.ascii_letters + string.digits + '!@#$%^&*'
    while True:
        pwd = ''.join(secrets.choice(alphabet) for _ in range(length))
        if (any(c.isupper()  for c in pwd)
                and any(c.islower()  for c in pwd)
                and any(c.isdigit()  for c in pwd)
                and any(c in '!@#$%^&*' for c in pwd)):
            return pwd


def _add_to_group(user: CustomUser, group_name: str):
    """Add user to a Django auth Group; silently skip if not found."""
    try:
        user.groups.add(Group.objects.get(name=group_name))
    except Group.DoesNotExist:
        pass


# ══════════════════════════════════════════════════════════════════════════════
#   AUTH VIEWS
# ══════════════════════════════════════════════════════════════════════════════

def _process_login(request, form, template_name):
    """
    Shared login processing logic used by both portal views.
    Handles POST authentication, remember-me session, flash messages,
    and role-based dashboard redirect.
    """
    if request.user.is_authenticated:
        return redirect(get_dashboard_url(request.user))

    if request.method == 'POST':
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            if not form.cleaned_data.get('remember_me'):
                request.session.set_expiry(0)

            messages.success(
                request,
                f'Welcome back, {user.get_full_name() or user.username}!'
            )
            next_url = request.GET.get('next') or get_dashboard_url(user)
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid credentials. Please check and try again.')

    return render(request, template_name, {'form': form, 'page_title': 'Sign In'})


def standard_login_view(request):
    """
    Phase 4: Standard portal — for Applicants and Admins.
    Credential hint: Email Address.
    URL: /accounts/login/
    """
    form = StandardLoginForm(request, data=request.POST or None)
    return _process_login(request, form, 'accounts/login_standard.html')


def staff_donor_login_view(request):
    """
    Phase 4: Staff & Donor portal — for Members, Reviewers, and Donors.
    Credential hint: Unique ID (KBD-0001, KBM-0003, etc.)
    URL: /accounts/portal-login/
    """
    form = StaffDonorLoginForm(request, data=request.POST or None)
    return _process_login(request, form, 'accounts/login_staff.html')


# Backward-compat alias: anything pointing at login_view still works
login_view = standard_login_view




def logout_view(request):
    """POST-only logout (CSRF-protected via form in base.html)."""
    next_url = request.POST.get('next') or request.GET.get('next')
    if request.method == 'POST':
        logout(request)
        messages.info(request, 'You have been logged out successfully.')
    if next_url:
        return redirect(next_url)
    return redirect('accounts:login')


# ══════════════════════════════════════════════════════════════════════════════
#   APPLICANT SELF-REGISTRATION  (updated: sends welcome email)
# ══════════════════════════════════════════════════════════════════════════════

def register_view(request):
    """
    Public registration — creates Applicant accounts only.
    Phase 2: Sends a 'Welcome to KB Foundation' email on success.
    """
    if request.user.is_authenticated:
        return redirect(get_dashboard_url(request.user))

    form = ApplicantRegistrationForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            user = form.save()
            login(request, user)

            # Phase 2: Dispatch welcome email
            login_url = request.build_absolute_uri(reverse('accounts:login'))
            send_welcome_applicant_email(user, login_url)

            messages.success(
                request,
                'Your account has been created. '
                'A welcome email has been sent to your inbox. '
                'You can now apply for a scholarship!'
            )
            return redirect('reports:applicant_dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')

    return render(request, 'accounts/register.html', {'form': form, 'page_title': 'Create Account'})


# ══════════════════════════════════════════════════════════════════════════════
#   PROFILE
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def profile_view(request):
    """Display the current user's profile details."""
    return render(request, 'accounts/profile.html', {
        'page_title': 'My Profile',
        'user_obj':   request.user,
    })


# ══════════════════════════════════════════════════════════════════════════════
#   ADMIN ONBOARDING VIEWS  (Phase 2)
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@role_required('admin')
def admin_register_member(request):
    """
    Admin-only: Create a new Member-role portal account.

    Flow:
      1. Admin fills in name / username / email.
      2. Backend auto-generates a secure 12-char temporary password.
      3. User is created with requires_password_change = True.
      4. Credentials email is sent to the new member's inbox.
      5. Admin sees a success flash with the temp password for their records.
    """
    form = AdminRegisterMemberForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            raw_password = _generate_password()

            user = form.save(commit=False)
            user.role                      = CustomUser.Role.MEMBER
            user.username                  = f"{user.role}_{uuid.uuid4().hex[:8]}"
            user.requires_password_change  = True
            user.set_password(raw_password)
            user.save()
            user.refresh_from_db()
            CustomUser.objects.filter(pk=user.pk).update(username=user.unique_id)
            user.username = user.unique_id

            _add_to_group(user, 'Member')

            # Dispatch credentials email with strict error catching
            login_url = request.build_absolute_uri(reverse('accounts:portal_login'))
            email_error = None
            try:
                send_credentials_email(user, raw_password, login_url)
            except Exception as e:
                email_error = str(e)

            # Fire in-app Notifications to Members
            from core.models import Notification
            members = CustomUser.objects.filter(role=CustomUser.Role.MEMBER, is_active=True)
            Notification.objects.bulk_create([
                Notification(user=u, message=f"New Member {user.get_full_name() or user.username} has been added to the system.")
                for u in members
            ])

            if email_error:
                messages.warning(
                    request,
                    f"Member created, but credentials email failed to send. Error: {email_error}"
                )
            else:
                messages.success(request, "Member successfully created.")
            return redirect('accounts:admin_register_member')
        else:
            messages.error(request, 'Please correct the errors highlighted below.')

    return render(request, 'accounts/admin_register_member.html', {
        'page_title': 'Register New Member',
        'form':       form,
    })


@login_required
@role_required('admin')
def admin_register_donor(request):
    """
    Admin-only: Create a new Donor-role portal account and matching Donor profile.

    Flow:
      1. Admin fills in name / email + optional donor profile fields (username auto-generated).
      2. Backend auto-generates a secure 12-char temporary password.
      3. CustomUser is created with role=DONOR, requires_password_change=True.
      4. A linked Donor profile record is created using the same personal details.
      5. Credentials email is sent to the new donor's inbox (with strict error catching).
      6. Admin sees a success flash with temp password for their records.
    """
    from donors.models import Donor

    form = AdminRegisterDonorForm(request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            raw_password = _generate_password()

            user = form.save(commit=False)
            user.role                      = CustomUser.Role.DONOR
            user.username                  = f"{user.role}_{uuid.uuid4().hex[:8]}"
            user.requires_password_change  = True
            user.set_password(raw_password)
            user.save()
            user.refresh_from_db()
            CustomUser.objects.filter(pk=user.pk).update(username=user.unique_id)
            user.username = user.unique_id

            _add_to_group(user, 'Donor')

            # Create the linked Donor profile
            Donor.objects.create(
                user      = user,
                full_name = user.get_full_name() or user.username,
                email     = user.email,
                phone     = form.cleaned_data.get('phone', ''),
                address   = form.cleaned_data.get('address', ''),
                notes     = form.cleaned_data.get('notes', ''),
            )

            # Dispatch credentials email with strict error catching
            login_url = request.build_absolute_uri(reverse('accounts:portal_login'))
            email_error = None
            try:
                send_credentials_email(user, raw_password, login_url)
            except Exception as e:
                email_error = str(e)

            # Fire in-app Notifications to Members
            from core.models import Notification
            members = CustomUser.objects.filter(role=CustomUser.Role.MEMBER, is_active=True)
            Notification.objects.bulk_create([
                Notification(user=u, message=f"New Donor {user.get_full_name() or user.username} has been added to the system.")
                for u in members
            ])

            if email_error:
                messages.warning(
                    request,
                    f"Donor created, but credentials email failed to send. Error: {email_error}"
                )
            else:
                messages.success(request, "Donor successfully created.")
            return redirect('accounts:admin_register_donor')
        else:
            messages.error(request, 'Please correct the errors highlighted below.')

    return render(request, 'accounts/admin_register_donor.html', {
        'page_title': 'Register New Donor',
        'form':       form,
    })


# ══════════════════════════════════════════════════════════════════════════════
#   FORCED PASSWORD CHANGE  (Phase 2)
# ══════════════════════════════════════════════════════════════════════════════

@login_required
def force_password_change(request):
    """
    First-login forced password change.
    Triggered automatically by ForcePasswordChangeMiddleware when
    request.user.requires_password_change is True.

    On success:
      - Password is updated via form.save()
      - requires_password_change is set to False
      - Session auth hash is refreshed (prevents logout)
      - User is redirected to their role-specific dashboard
    """
    # If they don't actually need to change password, send them home
    if not request.user.requires_password_change:
        return redirect(get_dashboard_url(request.user))

    form = StyledPasswordChangeForm(request.user, request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            user = form.save()

            # Clear the forced-change flag
            user.requires_password_change = False
            user.save(update_fields=['requires_password_change'])

            # Keep the session alive so they don't get logged out
            update_session_auth_hash(request, user)

            messages.success(
                request,
                'Your password has been changed successfully. Welcome to your dashboard!'
            )
            return redirect(get_dashboard_url(user))
        else:
            messages.error(request, 'Please correct the errors highlighted below.')

    return render(request, 'accounts/force_password_change.html', {
        'page_title': 'Change Your Password',
        'form':       form,
    })
