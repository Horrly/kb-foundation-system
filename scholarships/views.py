"""
scholarships/views.py  (full — Day 9/10 + Day 11 review workflow)
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import IntegrityError
from django.utils import timezone

from accounts.decorators import role_required
from .models import ScholarshipApplication, Document, ScholarshipRecipient
from .forms import ApplicationForm, DocumentForm, ReviewForm, AwardForm


# ── Shared helper ─────────────────────────────────────────────────────────────

def get_applicant_application(user):
    return ScholarshipApplication.objects.filter(applicant=user).first()


# ══════════════════════════════════════════════════════════════════════════════
#   APPLICANT VIEWS  (Days 9 & 10)
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@role_required('applicant')
def application_create(request):
    existing = get_applicant_application(request.user)
    if existing:
        messages.info(request, 'You already have an application on record.')
        return redirect('scholarships:application_status')

    form = ApplicationForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            try:
                application           = form.save(commit=False)
                application.applicant = request.user
                application.status    = ScholarshipApplication.Status.PENDING
                application.save()
                messages.success(
                    request,
                    '🎉 Application submitted! Please upload your supporting documents below.'
                )
                return redirect('scholarships:application_status')
            except IntegrityError:
                messages.error(request, 'You already have an application for this session.')
        else:
            messages.error(request, 'Please correct the errors highlighted below.')

    return render(request, 'scholarships/application_form.html', {
        'page_title': 'Apply for a Scholarship',
        'form': form,
        'form_action': 'Submit Application',
    })


@login_required
@role_required('applicant')
def application_status(request):
    application = get_applicant_application(request.user)
    recipient   = None
    documents   = []
    missing_types = set()

    if application:
        documents = application.documents.all()
        if application.status == ScholarshipApplication.Status.APPROVED:
            recipient = getattr(application, 'recipient_record', None)
        uploaded_types = set(documents.values_list('document_type', flat=True))
        all_types      = {dt.value for dt in Document.DocumentType}
        missing_types  = all_types - uploaded_types

    return render(request, 'scholarships/application_status.html', {
        'page_title':    'My Application Status',
        'application':   application,
        'documents':     documents,
        'recipient':     recipient,
        'missing_types': missing_types,
        'doc_type_labels': dict(Document.DocumentType.choices),
    })


@login_required
@role_required('applicant')
def document_upload(request):
    application = get_applicant_application(request.user)
    if not application:
        messages.warning(request, 'Submit an application before uploading documents.')
        return redirect('scholarships:application_create')

    locked = [ScholarshipApplication.Status.APPROVED, ScholarshipApplication.Status.REJECTED]
    if application.status in locked:
        messages.info(request, f'Your application is {application.get_status_display()}. Uploads are locked.')
        return redirect('scholarships:application_status')

    form = DocumentForm(request.POST or None, request.FILES or None)
    if request.method == 'POST':
        if form.is_valid():
            doc             = form.save(commit=False)
            doc.application = application
            doc.save()
            messages.success(request, f'"{doc.get_document_type_display()}" uploaded successfully.')
            return redirect('scholarships:application_status')
        else:
            messages.error(request, 'Upload failed. Please check the file and try again.')

    return render(request, 'scholarships/document_form.html', {
        'page_title':    'Upload Document',
        'form':          form,
        'application':   application,
        'existing_docs': application.documents.all(),
        'form_action':   'Upload Document',
    })


# ══════════════════════════════════════════════════════════════════════════════
#   STAFF VIEWS  (Day 11 — Review Workflow)
# ══════════════════════════════════════════════════════════════════════════════

@login_required
@role_required('admin', 'member', 'reviewer')
def application_list(request):
    """Staff view: all applications with status tab-filter and KPI counts."""
    qs = ScholarshipApplication.objects.select_related('applicant').all()

    status_filter = request.GET.get('status', '')
    if status_filter:
        qs = qs.filter(status=status_filter)

    counts = {
        s.value: ScholarshipApplication.objects.filter(status=s.value).count()
        for s in ScholarshipApplication.Status
    }

    return render(request, 'scholarships/application_list.html', {
        'page_title':     'Scholarship Applications',
        'applications':   qs,
        'status_choices': ScholarshipApplication.Status.choices,
        'current_status': status_filter,
        'counts':         counts,
        'total':          ScholarshipApplication.objects.count(),
    })


@login_required
@role_required('admin', 'member', 'reviewer')
def application_detail_staff(request, pk):
    """Staff view: full application detail with all documents and review form."""
    application = get_object_or_404(
        ScholarshipApplication.objects.select_related('applicant'), pk=pk
    )
    documents = application.documents.all()
    recipient = getattr(application, 'recipient_record', None)
    review_form = ReviewForm(instance=application)
    award_form  = AwardForm(
        instance=recipient,
        initial={'awarded_date': timezone.now().date()},
    ) if not recipient else AwardForm(instance=recipient)

    return render(request, 'scholarships/application_detail_staff.html', {
        'page_title':   f'Application — {application.applicant.get_full_name() or application.applicant.username}',
        'application':  application,
        'documents':    documents,
        'recipient':    recipient,
        'review_form':  review_form,
        'award_form':   award_form,
    })


@login_required
@role_required('admin', 'member', 'reviewer')
def application_review(request, pk):
    """
    POST-only: update an application's status + reviewer notes.
    Admins and Members can move to any status.
    Reviewers can only move to 'under_review' (not approve/reject).
    """
    application = get_object_or_404(ScholarshipApplication, pk=pk)

    if request.method != 'POST':
        return redirect('scholarships:application_detail_staff', pk=pk)

    form = ReviewForm(request.POST, instance=application)
    if form.is_valid():
        new_status = form.cleaned_data['status']

        # Reviewers cannot approve or reject — enforce RBAC at action level
        if (request.user.role == 'reviewer'
                and new_status in [
                    ScholarshipApplication.Status.APPROVED,
                    ScholarshipApplication.Status.REJECTED,
                ]):
            messages.error(
                request,
                'Reviewers can mark applications as "Under Review" only. '
                'Final decisions require Admin.'
            )
            return redirect('scholarships:application_detail_staff', pk=pk)

        # Members are read-only for final decisions — enforce at view level
        if (request.user.role == 'member'
                and new_status in [
                    ScholarshipApplication.Status.APPROVED,
                    ScholarshipApplication.Status.REJECTED,
                ]):
            messages.error(
                request,
                'Unauthorized. Members have read-only access. '
                'Only Administrators can approve or reject applications.'
            )
            return redirect('scholarships:application_detail_staff', pk=pk)

        old_status = application.status
        form.save()

        # Trigger Phase 6 Notifications & Email
        if old_status != new_status and new_status in [
            ScholarshipApplication.Status.APPROVED, 
            ScholarshipApplication.Status.REJECTED
        ]:
            from core.models import Notification
            from accounts.models import CustomUser
            from django.core.mail import send_mail
            
            action_text = "Approved" if new_status == ScholarshipApplication.Status.APPROVED else "Rejected"
            
            # a) Notify Members
            members = CustomUser.objects.filter(role=CustomUser.Role.MEMBER, is_active=True)
            Notification.objects.bulk_create([
                Notification(user=u, message=f"Scholarship application for {application.applicant.get_full_name() or application.applicant.username} has been {action_text}.")
                for u in members
            ])
            
            # b) Notify Applicant
            Notification.objects.create(
                user=application.applicant,
                message=f"Your scholarship application has been {action_text}."
            )
            
            # c) Console email to applicant
            send_mail(
                subject=f'Application {action_text}',
                message=f'Hello {application.applicant.get_full_name() or application.applicant.username},\n\nYour scholarship application has been {action_text}. Please check your dashboard for more details.\n\nThank you,\nKB Foundation',
                from_email='noreply@kbfoundation.org',
                recipient_list=[application.applicant.email],
                fail_silently=True,
            )

        messages.success(
            request,
            f'Application status updated to "{application.get_status_display()}".'
        )
    else:
        messages.error(request, 'Review update failed. Please check the form.')

    return redirect('scholarships:application_detail_staff', pk=pk)


@login_required
@role_required('admin', 'member')
def award_scholarship(request, pk):
    """
    POST-only: create or update the ScholarshipRecipient record for an
    approved application. Automatically sets status to APPROVED.
    Admin and Member only.
    """
    application = get_object_or_404(ScholarshipApplication, pk=pk)

    if request.method != 'POST':
        return redirect('scholarships:application_detail_staff', pk=pk)

    recipient = getattr(application, 'recipient_record', None)
    form = AwardForm(request.POST, instance=recipient)

    if form.is_valid():
        old_status         = application.status
        award              = form.save(commit=False)
        award.application  = application
        award.save()
        # Ensure application is marked approved
        application.status = ScholarshipApplication.Status.APPROVED
        application.save()

        if old_status != ScholarshipApplication.Status.APPROVED:
            from core.models import Notification
            from accounts.models import CustomUser
            from django.core.mail import send_mail
            
            # a) Notify Members
            members = CustomUser.objects.filter(role=CustomUser.Role.MEMBER, is_active=True)
            Notification.objects.bulk_create([
                Notification(user=u, message=f"Scholarship application for {application.applicant.get_full_name() or application.applicant.username} has been Approved.")
                for u in members
            ])
            
            # b) Notify Applicant
            Notification.objects.create(
                user=application.applicant,
                message=f"Your scholarship application has been Approved."
            )
            
            # c) Console email to applicant
            send_mail(
                subject='Application Approved',
                message=f'Hello {application.applicant.get_full_name() or application.applicant.username},\n\nYour scholarship application has been Approved. Please check your dashboard for more details.\n\nThank you,\nKB Foundation',
                from_email='noreply@kbfoundation.org',
                recipient_list=[application.applicant.email],
                fail_silently=True,
            )

        messages.success(
            request,
            f'Scholarship of ₦{award.amount_awarded:,} awarded to '
            f'{application.applicant.get_full_name() or application.applicant.username}.'
        )
    else:
        messages.error(request, 'Award form has errors. Please correct them.')

    return redirect('scholarships:application_detail_staff', pk=pk)
