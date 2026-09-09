"""
kb_project URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Password Reset
    path('password_reset/', auth_views.PasswordResetView.as_view(template_name='accounts/password_reset_form.html'), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='accounts/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='accounts/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='accounts/password_reset_complete.html'), name='password_reset_complete'),

    # Public-facing root → homepage (Phase 1)
    path('', include('core.urls', namespace='core')),

    # App namespaces
    path('accounts/',     include('accounts.urls',     namespace='accounts')),
    path('donors/',       include('donors.urls',        namespace='donors')),
    path('expenditures/', include('expenditures.urls',  namespace='expenditures')),
    path('scholarships/', include('scholarships.urls',  namespace='scholarships')),
    path('reports/',      include('reports.urls',       namespace='reports')),
]

# Serve uploaded media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
