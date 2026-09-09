from django.db import models
from django.conf import settings

class Notification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='User'
    )
    message = models.CharField(max_length=255, verbose_name='Message')
    is_read = models.BooleanField(default=False, verbose_name='Read Status')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created At')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'

    def __str__(self):
        return f"To {self.user.username}: {self.message}"

class Event(models.Model):
    class EventType(models.TextChoices):
        SCREENING = 'screening', 'Screening Exam'
        INTERVIEW = 'interview', 'Interview'
        CEREMONY = 'ceremony', 'Award Ceremony'
        GENERAL = 'general', 'General'

    title = models.CharField(max_length=200)
    event_type = models.CharField(max_length=20, choices=EventType.choices, default=EventType.GENERAL)
    date = models.DateField()
    time = models.TimeField()
    location = models.CharField(max_length=255)
    description = models.TextField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_events')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date', 'time']

    def __str__(self):
        return f"{self.title} - {self.date}"
