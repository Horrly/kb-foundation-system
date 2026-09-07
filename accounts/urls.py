from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # ── Phase 4: Split login portals ─────────────────────────────────────
    # Standard portal  → Applicants & Admins (login by email)
    path('login/',          views.standard_login_view,    name='login'),
    # Staff/Donor portal → Members, Reviewers & Donors (login by Unique ID)
    path('portal-login/',   views.staff_donor_login_view, name='portal_login'),

    # ── Auth ──────────────────────────────────────────────────────────────
    path('logout/',         views.logout_view,             name='logout'),
    path('register/',       views.register_view,           name='register'),
    path('profile/',        views.profile_view,            name='profile'),

    # ── Phase 2: Forced Password Change ──────────────────────────────────
    path('change-password/', views.force_password_change,  name='force_password_change'),

    # ── Phase 2: Admin Onboarding ─────────────────────────────────────────
    path('onboard/member/', views.admin_register_member,   name='admin_register_member'),
    path('onboard/donor/',  views.admin_register_donor,    name='admin_register_donor'),
]
