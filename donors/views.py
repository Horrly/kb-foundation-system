"""
donors/views.py

CRUD views for Donor and Donation (Admin/Member).
Phase 3 additions: Donor self-submission, pending queue, admin verification.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from django.utils import timezone
from django.urls import reverse

from accounts.decorators import role_required
from .models import Donor, Donation
from .forms import DonorForm, DonationForm, DonationSubmissionForm, DonationVerifyForm
from .filters import DonorFilter, DonationFilter
from .emails import (
    send_incoming_donation_alert,
    send_donation_confirmed_email,
    send_donation_rejected_email,
)


# ════════════════════════════════════════════════════════════════════════════════
#  DONOR VIEWS  (Admin / Member)
# ════════════════════════════════════════════════════════════════════════════════

@login_required
@role_required('admin', 'member')
def donor_list(request):
    """Paginated, searchable list of all donors."""
    donors_qs       = Donor.objects.all()
    f               = DonorFilter(request.GET, queryset=donors_qs)
    total_donors    = donors_qs.count()
    total_donations = (
        Donation.objects
        .filter(status=Donation.Status.CONFIRMED)
        .aggregate(total=Sum('amount'))['total'] or 0
    )

    context = {
        'page_title':      'Donors',
        'filter':          f,
        'donors':          f.qs,
        'total_donors':    total_donors,
        'total_donations': total_donations,
    }
    return render(request, 'donors/donor_list.html', context)


@login_required
@role_required('admin', 'member')
def donor_create(request):
    """Add a new donor."""
    form = DonorForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        donor = form.save()
        messages.success(request, f'Donor "{donor.full_name}" added successfully.')
        return redirect('donors:donor_detail', pk=donor.pk)
    elif request.method == 'POST':
        messages.error(request, 'Please correct the errors below.')

    return render(request, 'donors/donor_form.html', {
        'page_title': 'Add New Donor',
        'form':       form,
        'form_action':'Add Donor',
    })


@login_required
@role_required('admin', 'member')
def donor_update(request, pk):
    """Edit an existing donor's details."""
    donor = get_object_or_404(Donor, pk=pk)
    form  = DonorForm(request.POST or None, instance=donor)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Donor "{donor.full_name}" updated successfully.')
        return redirect('donors:donor_detail', pk=donor.pk)
    elif request.method == 'POST':
        messages.error(request, 'Please correct the errors below.')

    return render(request, 'donors/donor_form.html', {
        'page_title':  f'Edit — {donor.full_name}',
        'form':        form,
        'donor':       donor,
        'form_action': 'Save Changes',
    })


@login_required
@role_required('admin', 'member')
def donor_detail(request, pk):
    """Full donor profile: personal info + donation history + aggregated totals."""
    donor     = get_object_or_404(Donor, pk=pk)
    donations = donor.donations.all()
    f         = DonationFilter(request.GET, queryset=donations)

    return render(request, 'donors/donor_detail.html', {
        'page_title':     donor.full_name,
        'donor':          donor,
        'filter':         f,
        'donations':      f.qs,
        'total_donated':  donor.total_donated(),
        'donation_count': donor.donation_count(),
    })


@login_required
@role_required('admin')
def donor_delete(request, pk):
    """Delete a donor (and cascade-delete their donations)."""
    donor = get_object_or_404(Donor, pk=pk)
    if request.method == 'POST':
        name = donor.full_name
        donor.delete()
        messages.success(request, f'Donor "{name}" and all their donations have been deleted.')
        return redirect('donors:donor_list')

    return render(request, 'donors/donor_confirm_delete.html', {
        'page_title': f'Delete — {donor.full_name}',
        'donor':      donor,
    })


# ════════════════════════════════════════════════════════════════════════════════
#  DONATION VIEWS  (Admin / Member — staff management)
# ════════════════════════════════════════════════════════════════════════════════

@login_required
@role_required('admin', 'member')
def donation_list(request):
    """Filterable list of all donations across all donors."""
    donations_qs = Donation.objects.select_related('donor').all()
    f            = DonationFilter(request.GET, queryset=donations_qs)
    grand_total  = (
        f.qs
        .filter(status=Donation.Status.CONFIRMED)
        .aggregate(total=Sum('amount'))['total'] or 0
    )

    return render(request, 'donors/donation_list.html', {
        'page_title':  'Donations',
        'filter':      f,
        'donations':   f.qs,
        'grand_total': grand_total,
    })


@login_required
@role_required('admin', 'member')
def donation_create(request):
    """Record a new donation (staff side — bypasses pending workflow)."""
    # View-level RBAC: Members should not create donations directly.
    # The UI hides this link from Members; this guard blocks direct POST attempts.
    if request.method == 'POST' and request.user.role == 'member':
        messages.error(request, 'Unauthorized. Only Administrators can record donations directly.')
        return redirect('donors:donation_list')

    initial  = {}
    donor_pk = request.GET.get('donor')
    if donor_pk:
        try:
            initial['donor'] = Donor.objects.get(pk=donor_pk)
        except Donor.DoesNotExist:
            pass

    form = DonationForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        donation        = form.save(commit=False)
        donation.status = Donation.Status.CONFIRMED   # staff entry goes straight to confirmed
        donation.save()
        messages.success(
            request,
            f'Donation of ₦{donation.amount:,} from "{donation.donor.full_name}" recorded.'
        )
        return redirect('donors:donor_detail', pk=donor_pk) if donor_pk else redirect('donors:donation_list')
    elif request.method == 'POST':
        messages.error(request, 'Please correct the errors below.')

    return render(request, 'donors/donation_form.html', {
        'page_title':  'Record New Donation',
        'form':        form,
        'form_action': 'Record Donation',
    })


# ════════════════════════════════════════════════════════════════════════════════
#  PHASE 26: MAKE DONATION (Bank Transfer Info) & DONOR SELF-SUBMISSION
# ════════════════════════════════════════════════════════════════════════════════

@login_required
@role_required('donor')
def make_donation(request):
    """
    Displays Foundation Bank Account details and instructions for donors to make a transfer.
    """
    return render(request, 'donors/make_donation.html', {
        'page_title': 'Make a Donation',
        'bank_name': 'First Bank of Nigeria',
        'account_name': 'KB Foundation Community Fund',
        'account_number': '2034891204',
        'sort_code': '011151003',
        'swift_code': 'FBNINGLA',
    })


@login_required
@role_required('donor')
def donor_submit_donation(request):
    """
    Allows a Donor-role user to log their own donation.

    Flow:
      1. Donor fills in amount, date, payment method, reference no., receipt.
      2. Donation saved with status='pending'.
      3. Email alert fired to all Admins and Members.
      4. Donor redirected to their dashboard with a success message.
    """
    # Resolve the linked Donor profile
    donor_profile = getattr(request.user, 'donor_profile', None)
    if donor_profile is None:
        messages.error(
            request,
            'Your account is not linked to a Donor profile. '
            'Please contact the administrator.'
        )
        return redirect('reports:donor_dashboard')

    form = DonationSubmissionForm(
        request.POST or None,
        request.FILES or None,
    )

    if request.method == 'POST' and form.is_valid():
        donation             = form.save(commit=False)
        donation.donor       = donor_profile
        donation.status      = Donation.Status.PENDING
        donation.save()

        # Fire alert email to Admins + Members
        review_url = request.build_absolute_uri(
            reverse('donors:pending_donations')
        )
        send_incoming_donation_alert(donation, review_url)

        # Fire in-app Notifications to Admins (and Members)
        from core.models import Notification
        from accounts.models import CustomUser
        admin_users = CustomUser.objects.filter(
            role=CustomUser.Role.ADMIN, 
            is_active=True
        )
        Notification.objects.bulk_create([
            Notification(
                user=u, 
                message=f"New pending donation logged by {donation.donor.full_name}."
            ) for u in admin_users
        ])
        # Also notify Members
        member_users = CustomUser.objects.filter(
            role=CustomUser.Role.MEMBER, 
            is_active=True
        )
        Notification.objects.bulk_create([
            Notification(
                user=u, 
                message=f"New pending donation of ₦{donation.amount:,.2f} logged by {donation.donor.full_name}."
            ) for u in member_users
        ])

        messages.success(
            request,
            f'Your donation of \u20a6{donation.amount:,} has been submitted successfully! '
            'Our team will verify it and notify you once confirmed. '
            'Your Reference: <strong>'
            f'{donation.reference_number or "N/A"}</strong>'
        )
        return redirect('reports:donor_dashboard')
    elif request.method == 'POST':
        messages.error(request, 'Please correct the errors highlighted below.')

    return render(request, 'donors/submit_donation.html', {
        'page_title':     'Log a Donation',
        'form':           form,
        'donor_profile':  donor_profile,
    })


# ════════════════════════════════════════════════════════════════════════════════
#  PHASE 3: PENDING DONATION QUEUE  (Admin + Member)
# ════════════════════════════════════════════════════════════════════════════════

@login_required
@role_required('admin', 'member')
def pending_donation_list(request):
    """
    Lists all pending donations awaiting verification.
    Members: read-only view + can download receipts.
    Admins:  additionally get the "Verify" action button.
    """
    pending_qs = (
        Donation.objects
        .filter(status=Donation.Status.PENDING)
        .select_related('donor')
        .order_by('recorded_at')   # Oldest first — FIFO review queue
    )

    total_pending_value = pending_qs.aggregate(total=Sum('amount'))['total'] or 0

    return render(request, 'donors/pending_donation_list.html', {
        'page_title':          'Pending Donations',
        'pending_donations':   pending_qs,
        'total_pending_value': total_pending_value,
        'can_verify':          request.user.role == 'admin',
    })


# ════════════════════════════════════════════════════════════════════════════════
#  PHASE 3: ADMIN DONATION VERIFICATION
# ════════════════════════════════════════════════════════════════════════════════

@login_required
@role_required('admin')
def verify_donation(request, pk):
    """
    Admin-only: Review a pending donation and either approve or reject it.

    Approve:
      - Sets status = 'confirmed', amount_confirmed = form value, reviewed_at = now.
      - Fires confirmation email to Donor + Members.

    Reject:
      - Sets status = 'rejected', admin_notes = rejection reason, reviewed_at = now.
      - Fires rejection email to Donor.
    """
    donation = get_object_or_404(Donation, pk=pk, status=Donation.Status.PENDING)

    if request.method == 'POST':
        form = DonationVerifyForm(request.POST)
        if form.is_valid():
            action      = form.cleaned_data['action']
            now         = timezone.now()

            # Resolve Donor's portal user account (for email dispatch)
            donor_user = getattr(donation.donor, 'user', None)

            from django.core.mail import send_mail
            from django.conf import settings
            from core.models import Notification
            from accounts.models import CustomUser

            if action == DonationVerifyForm.ACTION_APPROVE:
                donation.status           = Donation.Status.CONFIRMED
                donation.amount_confirmed = form.cleaned_data['amount_confirmed']
                donation.reviewed_at      = now
                donation.save(update_fields=['status', 'amount_confirmed', 'reviewed_at'])

                admin_note_txt = f" Note: {donation.admin_note}" if donation.admin_note else ""
                confirmed_msg = f"Donation of ₦{donation.amount_confirmed:,.2f} from {donation.donor.full_name} was Confirmed.{admin_note_txt}"

                # Notify Donor (if user account exists)
                if donor_user:
                    Notification.objects.create(
                        user=donor_user,
                        message=f"Your donation of ₦{donation.amount_confirmed:,.2f} has been confirmed. Thank you!"
                    )
                    # Send direct email
                    send_mail(
                        subject="[KB Foundation] Donation Confirmed",
                        message=f"Dear {donation.donor.full_name},\n\nThank you for your generous donation of ₦{donation.amount_confirmed:,.2f}. It has been successfully confirmed.",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[donation.donor.email],
                        fail_silently=True,
                    )

                # Notify all Members
                members = CustomUser.objects.filter(role=CustomUser.Role.MEMBER, is_active=True)
                Notification.objects.bulk_create([
                    Notification(user=u, message=confirmed_msg)
                    for u in members
                ])

                messages.success(
                    request,
                    f'Donation of \u20a6{donation.amount:,} from '
                    f'<strong>{donation.donor.full_name}</strong> has been '
                    f'<span class="text-success">confirmed</span> at '
                    f'\u20a6{donation.amount_confirmed:,}. '
                    f'Email and system notifications sent.'
                )

            elif action == DonationVerifyForm.ACTION_NOT_CONFIRMED:
                donation.status      = Donation.Status.NOT_CONFIRMED
                donation.admin_note  = form.cleaned_data['admin_note']
                donation.reviewed_at = now
                donation.save(update_fields=['status', 'admin_note', 'reviewed_at'])

                rejection_reason = donation.admin_note or "No reason provided"
                rejected_member_msg = f"Donation of ₦{donation.amount:,.2f} from {donation.donor.full_name} was Not Confirmed. Reason: {rejection_reason}"

                # Notify Donor
                if donor_user:
                    Notification.objects.create(
                        user=donor_user,
                        message=f"Your donation of ₦{donation.amount:,.2f} was not confirmed. Please check your email for details."
                    )
                    # Send direct email
                    send_mail(
                        subject="[KB Foundation] Donation Not Confirmed",
                        message=f"Dear {donation.donor.full_name},\n\nYour recent donation could not be confirmed at this time.\n\nReason: {rejection_reason}\n\nPlease contact support or try uploading your receipt again.",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[donation.donor.email],
                        fail_silently=True,
                    )

                # Notify all Members
                members = CustomUser.objects.filter(role=CustomUser.Role.MEMBER, is_active=True)
                Notification.objects.bulk_create([
                    Notification(user=u, message=rejected_member_msg)
                    for u in members
                ])

                messages.warning(
                    request,
                    f'Donation from <strong>{donation.donor.full_name}</strong> was marked as '
                    f'<span class="text-warning">Not Confirmed</span>. '
                    f'The donor and members have been notified.'
                )

            return redirect('donors:pending_donations')
        # Form errors fall through to the GET render below
    else:
        form = DonationVerifyForm()

    return render(request, 'donors/verify_donation.html', {
        'page_title': f'Verify Donation — {donation.donor.full_name}',
        'donation':   donation,
        'form':       form,
    })


# ════════════════════════════════════════════════════════════════════════════════
#  PHASE 46: DONOR RECEIPT PRINT
# ════════════════════════════════════════════════════════════════════════════════

@login_required
def donor_receipt_view(request, donation_id):
    """
    Render a clean, professional PDF-ready tax receipt template.
    Accessible by the donor who made it or any admin/member.
    """
    donation = get_object_or_404(Donation.objects.select_related('donor'), pk=donation_id, status=Donation.Status.CONFIRMED)
    
    # Security: Ensure only the owning donor or an admin can view it.
    if request.user.role == 'donor':
        donor_profile = getattr(request.user, 'donor_profile', None)
        if donation.donor != donor_profile:
            messages.error(request, 'Unauthorized access to this receipt.')
            return redirect('reports:donor_dashboard')
            
    return render(request, 'donors/receipt_print.html', {
        'donation': donation,
    })
