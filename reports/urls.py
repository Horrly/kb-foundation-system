from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Generic redirect to role-specific dashboard
    path('dashboard/',          views.dashboard,          name='dashboard'),

    # Role-specific dashboards
    path('dashboard/admin/',     views.admin_dashboard,     name='admin_dashboard'),
    path('dashboard/member/',    views.member_dashboard,    name='member_dashboard'),
    path('dashboard/reviewer/',  views.reviewer_dashboard,  name='reviewer_dashboard'),
    path('dashboard/applicant/', views.applicant_dashboard, name='applicant_dashboard'),
    path('dashboard/donor/',     views.donor_dashboard,     name='donor_dashboard'),    # Phase 1

    # Summary Report (Admin + Member)
    path('summary/',             views.summary_report,      name='summary_report'),
]
