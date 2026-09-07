from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('notifications/read/', views.mark_notifications_read, name='mark_notifications_read'),
    path('notifications/<int:notif_id>/dismiss/', views.mark_single_notification_read, name='mark_single_notification_read'),
]
