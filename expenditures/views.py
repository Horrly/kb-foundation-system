"""
expenditures/views.py

CRUD views for Expenditure — Admin and Member access.
Delete is restricted to Admin only.
Includes category aggregation for the summary section.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count

from accounts.decorators import role_required
from .models import Expenditure
from .forms import ExpenditureForm
from .filters import ExpenditureFilter


# ---------------------------------------------------------------------------
# Category metadata: display label, Bootstrap colour, Bootstrap Icon
# Used to enrich the category summary cards in the list view
# ---------------------------------------------------------------------------
CATEGORY_META = {
    'scholarship_grants': {'color': '#1a3d5c', 'icon': 'bi-mortarboard-fill',    'bg': '#e8f0f7'},
    'administrative':     {'color': '#6c757d', 'icon': 'bi-building',             'bg': '#f0f0f0'},
    'events':             {'color': '#0d6efd', 'icon': 'bi-calendar-event-fill',  'bg': '#e8f0ff'},
    'marketing':          {'color': '#e8a020', 'icon': 'bi-megaphone-fill',       'bg': '#fef6e7'},
    'logistics':          {'color': '#198754', 'icon': 'bi-truck',                'bg': '#e8f5ed'},
    'other':              {'color': '#adb5bd', 'icon': 'bi-three-dots-vertical',  'bg': '#f5f5f5'},
}


def build_category_summary(queryset):
    """
    Return a list of dicts with per-category totals + UI metadata.
    Each dict: {label, key, total, count, color, icon, bg}
    """
    # ORM aggregation grouped by category
    raw = (
        queryset
        .values('category')
        .annotate(total=Sum('amount'), count=Count('id'))
        .order_by('category')
    )

    summary = []
    for row in raw:
        key  = row['category']
        meta = CATEGORY_META.get(key, CATEGORY_META['other'])
        label = dict(Expenditure.Category.choices).get(key, key)
        summary.append({
            'key':   key,
            'label': label,
            'total': row['total'] or 0,
            'count': row['count'],
            **meta,
        })
    return summary


# ============================================================
#  EXPENDITURE LIST (+ category summary)
# ============================================================
@login_required
@role_required('admin', 'member')
def expenditure_list(request):
    all_qs = Expenditure.objects.all()
    f      = ExpenditureFilter(request.GET, queryset=all_qs)

    # Aggregations
    grand_total      = f.qs.aggregate(total=Sum('amount'))['total'] or 0
    grand_total_all  = all_qs.aggregate(total=Sum('amount'))['total'] or 0
    category_summary = build_category_summary(all_qs)      # always on full set

    context = {
        'page_title':       'Expenditures',
        'filter':           f,
        'expenditures':     f.qs.select_related(),
        'grand_total':      grand_total,
        'grand_total_all':  grand_total_all,
        'category_summary': category_summary,
        'total_records':    all_qs.count(),
    }
    return render(request, 'expenditures/expenditure_list.html', context)


# ============================================================
#  CREATE
# ============================================================
@login_required
@role_required('admin', 'member')
def expenditure_create(request):
    # View-level RBAC: UI hides this from Members; guard blocks direct POST bypass.
    if request.method == 'POST' and request.user.role == 'member':
        messages.error(request, 'Unauthorized. Only Administrators can record expenditures.')
        return redirect('expenditures:expenditure_list')

    form = ExpenditureForm(request.POST or None, request.FILES or None)

    if request.method == 'POST':
        if form.is_valid():
            expenditure = form.save(commit=False)
            expenditure.recorded_by = request.user.get_full_name() or request.user.username
            expenditure.save()
            messages.success(
                request,
                f'Expenditure "{expenditure.title}" (₦{expenditure.amount:,}) recorded successfully.'
            )
            return redirect('expenditures:expenditure_list')
        else:
            messages.error(request, 'Please correct the errors below.')

    context = {
        'page_title':  'Record New Expenditure',
        'form':        form,
        'form_action': 'Record Expenditure',
    }
    return render(request, 'expenditures/expenditure_form.html', context)


# ============================================================
#  UPDATE
# ============================================================
@login_required
@role_required('admin', 'member')
def expenditure_update(request, pk):
    expenditure = get_object_or_404(Expenditure, pk=pk)
    form = ExpenditureForm(
        request.POST  or None,
        request.FILES or None,
        instance=expenditure,
    )

    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, f'Expenditure "{expenditure.title}" updated successfully.')
            return redirect('expenditures:expenditure_list')
        else:
            messages.error(request, 'Please correct the errors below.')

    context = {
        'page_title':   f'Edit — {expenditure.title}',
        'form':         form,
        'expenditure':  expenditure,
        'form_action':  'Save Changes',
    }
    return render(request, 'expenditures/expenditure_form.html', context)


# ============================================================
#  DELETE  (Admin only)
# ============================================================
@login_required
@role_required('admin')
def expenditure_delete(request, pk):
    expenditure = get_object_or_404(Expenditure, pk=pk)

    if request.method == 'POST':
        title = expenditure.title
        # Delete the physical receipt file to avoid orphan files in MEDIA_ROOT
        if expenditure.receipt:
            try:
                import os
                if os.path.isfile(expenditure.receipt.path):
                    os.remove(expenditure.receipt.path)
            except Exception:
                pass  # Don't block deletion if file is already missing
        expenditure.delete()
        messages.success(request, f'Expenditure "{title}" has been deleted.')
        return redirect('expenditures:expenditure_list')

    context = {
        'page_title':  f'Delete — {expenditure.title}',
        'expenditure': expenditure,
    }
    return render(request, 'expenditures/expenditure_confirm_delete.html', context)
