"""
kb_project URL Configuration
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

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
