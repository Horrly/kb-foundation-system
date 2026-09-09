"""
core/views.py — Public-facing views for the KB Foundation homepage.
"""

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required


def home(request):
    """
    Public homepage — accessible without authentication.
    """

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

    from .models import Event
    from django.utils import timezone
    events = Event.objects.filter(date__gte=timezone.now().date()).order_by('date', 'time')[:3]

    context = {
        'page_title':   'Home',
        'testimonials': testimonials,
        'events': events,
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

# ════════════════════════════════════════════════════════════════════════════════
#  PHASE 47: EVENTS MANAGEMENT
# ════════════════════════════════════════════════════════════════════════════════

def event_list(request):
    """Public view for listing all upcoming events."""
    from .models import Event
    from django.utils import timezone
    events = Event.objects.filter(date__gte=timezone.now().date()).order_by('date', 'time')
    return render(request, 'core/events.html', {'events': events, 'page_title': 'Upcoming Events'})


@login_required
def event_create(request):
    """Secretary/Admin view to create a new event and notify accepted applicants."""
    from .models import Event, Notification
    from scholarships.models import ScholarshipApplication
    from django.core.mail import send_mail
    from django.conf import settings
    from django.contrib import messages

    if request.user.role not in ['admin', 'member']:
        messages.error(request, 'Unauthorized. Only staff can create events.')
        return redirect('core:home')

    if request.method == 'POST':
        title = request.POST.get('title')
        event_type = request.POST.get('event_type')
        date = request.POST.get('date')
        time = request.POST.get('time')
        location = request.POST.get('location')
        description = request.POST.get('description')

        event = Event.objects.create(
            title=title,
            event_type=event_type,
            date=date,
            time=time,
            location=location,
            description=description,
            created_by=request.user
        )

        # Notify qualified applicants if it's screening or ceremony
        if event_type in [Event.EventType.SCREENING, Event.EventType.CEREMONY]:
            from django.db.models import Q
            if event_type == Event.EventType.SCREENING:
                accepted_apps = ScholarshipApplication.objects.filter(status=ScholarshipApplication.Status.ACCEPTED).select_related('applicant')
            else: # CEREMONY
                accepted_apps = ScholarshipApplication.objects.filter(
                    Q(status=ScholarshipApplication.Status.SCREENING_PASSED) | Q(status=ScholarshipApplication.Status.AWARDED)
                ).select_related('applicant')
            
            notification_objects = []
            emails = []
            
            for app in accepted_apps:
                applicant_user = app.applicant
                # On-site notification
                msg = f"Upcoming Event: {event.title} on {event.date} at {event.time}. Location: {event.location}."
                notification_objects.append(Notification(user=applicant_user, message=msg))
                # Email collection
                emails.append(applicant_user.email)
            
            if notification_objects:
                Notification.objects.bulk_create(notification_objects)
                
            if emails:
                send_mail(
                    subject=f"[KB Foundation] Upcoming Event: {event.title}",
                    message=f"Dear Scholar,\n\nPlease be informed of an upcoming event.\n\nTitle: {event.title}\nDate: {event.date}\nTime: {event.time}\nLocation: {event.location}\nDetails: {event.description}\n\nBest regards,\nKB Foundation",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=emails,
                    fail_silently=True,
                )
            messages.success(request, f'Event "{event.title}" created successfully. {len(emails)} scholars notified.')
        else:
            messages.success(request, f'Event "{event.title}" created successfully.')

        return redirect('core:event_list')

    # GET Request
    return render(request, 'core/event_form.html', {
        'page_title': 'Create New Event',
        'event_types': Event.EventType.choices
    })
