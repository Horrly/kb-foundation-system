"""
reports/views.py — Days 12-14
Full dashboard aggregation for all roles + a dedicated Summary Report view.
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q

from accounts.decorators import role_required


# ── Lazy imports to avoid circular dependency (models live in sibling apps) ──
def _donor_stats():
    from donors.models import Donor, Donation
    from django.db.models import Sum, Count
    total_donors    = Donor.objects.count()
    total_donations = Donation.objects.aggregate(total=Sum('amount'))['total'] or 0
    recent_donations = Donation.objects.select_related('donor').order_by('-date')[:5]
    return total_donors, total_donations, recent_donations


def _expenditure_stats():
    from expenditures.models import Expenditure
    from django.db.models import Sum, Count
    total_expenditures = Expenditure.objects.aggregate(total=Sum('amount'))['total'] or 0
    exp_count          = Expenditure.objects.count()
    return total_expenditures, exp_count


def _scholarship_stats():
    from scholarships.models import ScholarshipApplication, ScholarshipRecipient
    from django.db.models import Sum, Count
    total_apps    = ScholarshipApplication.objects.count()
    pending       = ScholarshipApplication.objects.filter(status='pending').count()
    under_review  = ScholarshipApplication.objects.filter(status='under_review').count()
    approved      = ScholarshipApplication.objects.filter(status='approved').count()
    rejected      = ScholarshipApplication.objects.filter(status='rejected').count()
    total_awarded = ScholarshipRecipient.objects.aggregate(total=Sum('amount_awarded'))['total'] or 0
    recipients    = ScholarshipRecipient.objects.count()
    return total_apps, pending, under_review, approved, rejected, total_awarded, recipients


def _recent_applications(limit=5):
    from scholarships.models import ScholarshipApplication
    return (ScholarshipApplication.objects
            .select_related('applicant')
            .order_by('-created_at')[:limit])


def _pending_applications(limit=10):
    from scholarships.models import ScholarshipApplication
    return (ScholarshipApplication.objects
            .filter(status__in=['pending', 'under_review'])
            .select_related('applicant')
            .order_by('created_at'))[:limit]


# ── Generic role-based redirect ───────────────────────────────────────────────
@login_required
def dashboard(request):
    """Redirect bare /reports/dashboard/ to the correct role dashboard."""
    role_map = {
        'admin':    'reports:admin_dashboard',
        'member':   'reports:member_dashboard',
        'reviewer': 'reports:reviewer_dashboard',
        'applicant':'reports:applicant_dashboard',
    }
    url_name = role_map.get(getattr(request.user, 'role', ''), 'accounts:login')
    return redirect(url_name)


# ── Admin Dashboard ───────────────────────────────────────────────────────────
@login_required
@role_required('admin')
def admin_dashboard(request):
    total_donors, total_donations, recent_donations = _donor_stats()
    total_expenditures, exp_count                    = _expenditure_stats()
    total_apps, pending, under_review, approved, rejected, total_awarded, recipients = _scholarship_stats()

    net_balance = total_donations - total_expenditures

    context = {
        'page_title': 'Admin Dashboard',
        # KPI values
        'total_donors':       total_donors,
        'total_donations':    total_donations,
        'total_expenditures': total_expenditures,
        'net_balance':        net_balance,
        'total_apps':         total_apps,
        'pending':            pending,
        'under_review':       under_review,
        'approved':           approved,
        'rejected':           rejected,
        'total_awarded':      total_awarded,
        'recipients':         recipients,
        'exp_count':          exp_count,
        # Recent data tables
        'recent_donations':   recent_donations,
        'recent_apps':        _recent_applications(),
    }
    return render(request, 'reports/admin_dashboard.html', context)


# ── Member Dashboard ──────────────────────────────────────────────────────────
@login_required
@role_required('member')
def member_dashboard(request):
    total_donors, total_donations, recent_donations = _donor_stats()
    total_expenditures, exp_count                    = _expenditure_stats()
    total_apps, pending, under_review, approved, rejected, total_awarded, recipients = _scholarship_stats()

    context = {
        'page_title':         'Member Dashboard',
        'total_donors':       total_donors,
        'total_donations':    total_donations,
        'total_expenditures': total_expenditures,
        'total_apps':         total_apps,
        'pending':            pending,
        'approved':           approved,
        'recipients':         recipients,
        'total_awarded':      total_awarded,
        'recent_donations':   recent_donations,
        'recent_apps':        _recent_applications(),
    }
    return render(request, 'reports/member_dashboard.html', context)


# ── Reviewer Dashboard ────────────────────────────────────────────────────────
@login_required
@role_required('reviewer')
def reviewer_dashboard(request):
    total_apps, pending, under_review, approved, rejected, total_awarded, recipients = _scholarship_stats()
    queue = _pending_applications()

    context = {
        'page_title':    'Reviewer Dashboard',
        'total_apps':    total_apps,
        'pending':       pending,
        'under_review':  under_review,
        'approved':      approved,
        'rejected':      rejected,
        'queue':         queue,
    }
    return render(request, 'reports/reviewer_dashboard.html', context)


# ── Applicant Dashboard ───────────────────────────────────────────────────────
@login_required
@role_required('applicant')
def applicant_dashboard(request):
    from scholarships.models import ScholarshipApplication, Document
    application = (ScholarshipApplication.objects
                   .filter(applicant=request.user)
                   .first())
    documents     = application.documents.all() if application else []
    doc_count     = len(documents)
    all_doc_types = {dt.value for dt in Document.DocumentType}
    uploaded_types = set(documents.values_list('document_type', flat=True)) if application else set()
    missing_types  = all_doc_types - uploaded_types

    context = {
        'page_title':    'My Dashboard',
        'application':   application,
        'documents':     documents,
        'doc_count':     doc_count,
        'missing_types': missing_types,
        'doc_type_labels': dict(Document.DocumentType.choices),
    }
    return render(request, 'reports/applicant_dashboard.html', context)


# ── Donor Dashboard (Phase 1) ────────────────────────────────────────────────
@login_required
@role_required('donor')
def donor_dashboard(request):
    """
    Personal dashboard for Donor-role users.
    Phase 3: Shows full donation history with status badges and submission CTA.
    """
    from donors.models import Donation

    donor_profile = getattr(request.user, 'donor_profile', None)

    if donor_profile:
        all_donations = donor_profile.donations.order_by('-date', '-recorded_at')
        total_given   = donor_profile.total_donated()
        pending_count  = all_donations.filter(status=Donation.Status.PENDING).count()
        confirmed_count = all_donations.filter(status=Donation.Status.CONFIRMED).count()
        rejected_count  = all_donations.filter(status=Donation.Status.REJECTED).count()
    else:
        all_donations   = []
        total_given     = 0
        pending_count   = 0
        confirmed_count = 0
        rejected_count  = 0

    context = {
        'page_title':      'My Donor Dashboard',
        'donor_profile':   donor_profile,
        'donations':       all_donations,
        'total_given':     total_given,
        'pending_count':   pending_count,
        'confirmed_count': confirmed_count,
        'rejected_count':  rejected_count,
        'total_submissions': (pending_count + confirmed_count + rejected_count),
    }
    return render(request, 'reports/donor_dashboard.html', context)



# ── Summary Report ────────────────────────────────────────────────────────────
@login_required
@role_required('admin', 'member')
def summary_report(request):
    """
    A single-page printable financial + scholarship summary report.
    """
    from expenditures.models import Expenditure
    from donors.models import Donation
    from django.db.models import Sum

    total_donors, total_donations, _ = _donor_stats()
    total_expenditures, _            = _expenditure_stats()
    total_apps, pending, under_review, approved, rejected, total_awarded, recipients = _scholarship_stats()

    # Expenditure breakdown by category
    exp_by_category = (
        Expenditure.objects
        .values('category')
        .annotate(total=Sum('amount'), count=Count('id'))
        .order_by('-total')
    )
    # Category label map
    from expenditures.models import Expenditure as Exp
    cat_labels = dict(Exp.Category.choices)
    for row in exp_by_category:
        row['label'] = cat_labels.get(row['category'], row['category'])

    # Donations by month (last 6)
    from django.utils import timezone
    from datetime import timedelta
    six_months_ago = timezone.now().date() - timedelta(days=180)
    donations_trend = (
        Donation.objects
        .filter(date__gte=six_months_ago)
        .extra(select={'month': "DATE_FORMAT(date, '%%Y-%%m')"})
        .values('month')
        .annotate(total=Sum('amount'))
        .order_by('month')
    )

    context = {
        'page_title':        'Financial Summary Report',
        'total_donors':      total_donors,
        'total_donations':   total_donations,
        'total_expenditures':total_expenditures,
        'net_balance':       total_donations - total_expenditures,
        'total_apps':        total_apps,
        'approved':          approved,
        'rejected':          rejected,
        'pending':           pending,
        'under_review':      under_review,
        'total_awarded':     total_awarded,
        'recipients':        recipients,
        'exp_by_category':   list(exp_by_category),
        'donations_trend':   list(donations_trend),
    }
    return render(request, 'reports/summary_report.html', context)
