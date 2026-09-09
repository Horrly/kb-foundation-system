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
        # Phase 45: Handle Bank Details Update
        if request.method == 'POST' and request.POST.get('action') == 'update_bank':
            if application.status in [ScholarshipApplication.Status.ACCEPTED, ScholarshipApplication.Status.AWARDED, ScholarshipApplication.Status.SCREENING_PASSED]:
                application.bank_name = request.POST.get('bank_name', '').strip()
                application.account_number = request.POST.get('account_number', '').strip()
                application.account_name = request.POST.get('account_name', '').strip()
                application.save(update_fields=['bank_name', 'account_number', 'account_name'])
                messages.success(request, "Bank details updated securely. Your disbursement is being processed.")
                return redirect('scholarships:application_status')

        documents = application.documents.all()
        if application.status in [ScholarshipApplication.Status.ACCEPTED, ScholarshipApplication.Status.AWARDED, ScholarshipApplication.Status.SCREENING_PASSED]:
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

    # Phase 41: Strict lockdown
    if getattr(application, 'is_submitted', False):
        messages.error(request, 'Your application has been locked for review. No further documents can be uploaded.')
        return redirect('scholarships:application_status')

    locked = [ScholarshipApplication.Status.ACCEPTED, ScholarshipApplication.Status.REJECTED]
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

@login_required
@role_required('applicant')
def application_submit(request):
    application = get_applicant_application(request.user)
    if not application:
        return redirect('scholarships:application_create')
        
    if request.method == 'POST':
        if not getattr(application, 'is_submitted', False):
            application.is_submitted = True
            application.save(update_fields=['is_submitted'])
            
            from django.core.mail import send_mail
            from django.conf import settings
            send_mail(
                subject='Application Submitted',
                message='Your application has been successfully submitted and will be reviewed.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[request.user.email],
                fail_silently=True,
            )
            messages.success(request, 'Your application has been successfully submitted and locked for review.')
        
    return redirect('scholarships:application_status')


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
                    ScholarshipApplication.Status.ACCEPTED,
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
                    ScholarshipApplication.Status.ACCEPTED,
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

        # Trigger Phase 6/41 Notifications & Email for ANY status change
        if old_status != new_status:
            from core.models import Notification
            from accounts.models import CustomUser
            from django.core.mail import send_mail
            from django.conf import settings
            
            action_text = application.get_status_display()
            
            # a) Notify Members (only for Approved/Rejected to avoid noise)
            if new_status in [ScholarshipApplication.Status.ACCEPTED, ScholarshipApplication.Status.REJECTED]:
                members = CustomUser.objects.filter(role=CustomUser.Role.MEMBER, is_active=True)
                Notification.objects.bulk_create([
                    Notification(user=u, message=f"Scholarship application for {application.applicant.get_full_name() or application.applicant.username} has been marked as {action_text}.")
                    for u in members
                ])
            
            # b) Notify Applicant (for all status changes)
            Notification.objects.create(
                user=application.applicant,
                message=f"Your scholarship application status has changed to: {action_text}."
            )
            
            # c) Console email to applicant
            send_mail(
                subject=f'[KB Foundation] Application Status Update',
                message=f'Hello {application.applicant.get_full_name() or application.applicant.username},\n\nYour scholarship application status has been updated to: {action_text}.\nPlease check your dashboard for more details.\n\nThank you,\nKB Foundation',
                from_email=settings.DEFAULT_FROM_EMAIL,
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
@role_required('member')
def member_recommend(request, pk):
    application = get_object_or_404(ScholarshipApplication, pk=pk)
    if request.method == 'POST':
        action = request.POST.get('recommendation')
        if action in ['Recommended', 'Not Recommended']:
            application.member_recommendation = action
            application.status = ScholarshipApplication.Status.RECOMMENDED if action == 'Recommended' else ScholarshipApplication.Status.IN_REVIEW
            application.save()
            messages.success(request, f'Application marked as {action}.')
    return redirect('scholarships:application_detail_staff', pk=pk)


@login_required
@role_required('admin')
def admin_decision(request, pk):
    application = get_object_or_404(ScholarshipApplication, pk=pk)
    if request.method == 'POST':
        action = request.POST.get('decision')
        old_status = application.status
        
        if action == 'Accept':
            application.status = ScholarshipApplication.Status.ACCEPTED
            application.save()
            messages.success(request, 'Application Accepted.')
            
            from django.core.mail import send_mail
            from django.conf import settings
            send_mail(
                subject='Congratulations! Application Accepted',
                message='Congratulations! Your application has been accepted. Please stay close to your email for updates regarding the next steps, such as screening exams.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[application.applicant.email],
                fail_silently=True,
            )
            
        elif action == 'Reject':
            application.status = ScholarshipApplication.Status.REJECTED
            application.save()
            messages.success(request, 'Application Rejected.')
            
            from django.core.mail import send_mail
            from django.conf import settings
            send_mail(
                subject='Application Update',
                message='Thank you for applying. We regret to inform you that your application was not successful at this time.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[application.applicant.email],
                fail_silently=True,
            )
            
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
        application.status = ScholarshipApplication.Status.ACCEPTED
        application.save()

        if old_status != ScholarshipApplication.Status.ACCEPTED:
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

@login_required
@role_required('admin')
def disburse_scholarship(request, pk):
    from expenditures.models import Expenditure
    from django.utils import timezone
    from django.contrib import messages
    if request.method == 'POST':
        application = get_object_or_404(ScholarshipApplication, pk=pk)
        amount = request.POST.get('disbursement_amount')
        if amount and application.bank_name:
            application.disbursement_amount = amount
            application.is_disbursed = True
            application.status = ScholarshipApplication.Status.DISBURSED
            application.save()

            Expenditure.objects.create(
                title=f"Scholarship Grant - {application.applicant.get_full_name() or application.applicant.username}",
                amount=amount,
                date=timezone.now().date(),
                category=Expenditure.Category.SCHOLARSHIP_GRANTS,
                notes=f"Bank: {application.bank_name}, Acct: {application.account_number}",
                recorded_by=request.user.username
            )
            messages.success(request, "Disbursement recorded and Expenditure created.")
    return redirect('scholarships:application_detail_staff', pk=pk)
