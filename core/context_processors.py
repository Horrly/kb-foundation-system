from .models import Notification

def unread_notifications(request):
    """
    Returns the count and a list of the latest 5 unread notifications
    for the authenticated user. Fails gracefully if not authenticated.
    """
    if request.user.is_authenticated:
        qs = Notification.objects.filter(user=request.user, is_read=False)
        return {
            'unread_notifications_count': qs.count(),
            'latest_notifications': qs[:5]
        }
    return {
        'unread_notifications_count': 0,
        'latest_notifications': []
    }
