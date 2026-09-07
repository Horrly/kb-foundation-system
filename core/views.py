"""
core/views.py — Public-facing views for the KB Foundation homepage.
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required


def home(request):
    """
    Public homepage — accessible without authentication.
    Authenticated users are silently redirected to their dashboard so
    returning staff members don't land on the marketing page.
    """
    if request.user.is_authenticated:
        from accounts.views import get_dashboard_url
        return redirect(get_dashboard_url(request.user))

    # Testimonial data — real success stories of past beneficiaries
    testimonials = [
        {
            'name':    'Aisha Bello',
            'session': '2022/2023',
            'course':  'Computer Science, UNILAG',
            'quote':   (
                'The KB Foundation scholarship changed the trajectory of my life. '
                'I was struggling to pay school fees, but this support allowed me '
                'to focus on my studies and graduate with a First Class degree.'
            ),
            'avatar':  'AB',
            'colour':  '#1a3d5c',
        },
        {
            'name':    'Chukwuemeka Okonkwo',
            'session': '2021/2022',
            'course':  'Medicine & Surgery, UNIBEN',
            'quote':   (
                'Without the KB Foundation, becoming a doctor would have remained '
                'a dream. Their support not just financial — the mentorship and '
                'community gave me the confidence to excel.'
            ),
            'avatar':  'CO',
            'colour':  '#198754',
        },
        {
            'name':    'Fatimah Adamu',
            'session': '2023/2024',
            'course':  'Accounting, ABU Zaria',
            'quote':   (
                'I applied on a whim and the process was seamless. The online portal '
                'made uploading documents simple, and the team communicated every step. '
                'I am now a proud KB Foundation Scholar!'
            ),
            'avatar':  'FA',
            'colour':  '#e8a020',
        },
        {
            'name':    'Daniel Okwu',
            'session': '2020/2021',
            'course':  'Electrical Engineering, OAU',
            'quote':   (
                'The scholarship relieved so much financial pressure from my family. '
                'I was able to complete my final year project and secure an internship '
                'with a top engineering firm. Forever grateful.'
            ),
            'avatar':  'DO',
            'colour':  '#6f42c1',
        },
    ]

    context = {
        'page_title':   'Home',
        'testimonials': testimonials,
    }
    return render(request, 'core/index.html', context)


@login_required
def mark_notifications_read(request):
    """Marks all unread notifications as read and redirects back."""
    from .models import Notification
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return redirect(request.META.get('HTTP_REFERER', 'core:home'))


@login_required
def mark_single_notification_read(request, notif_id):
    """Marks a single notification as read. Returns JSON for AJAX callers."""
    from .models import Notification
    from django.http import JsonResponse
    Notification.objects.filter(pk=notif_id, user=request.user).update(is_read=True)
    new_count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'status': 'success', 'unread_count': new_count})
