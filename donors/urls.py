from django.urls import path
from . import views

app_name = 'donors'

urlpatterns = [
    # ── Donor CRUD (Admin / Member) ───────────────────────────────────────
    path('',                    views.donor_list,   name='donor_list'),
    path('add/',                views.donor_create, name='donor_create'),
    path('<int:pk>/',           views.donor_detail, name='donor_detail'),
    path('<int:pk>/edit/',      views.donor_update, name='donor_update'),
    path('<int:pk>/delete/',    views.donor_delete, name='donor_delete'),

    # ── Donation Management (Admin / Member) ──────────────────────────────
    path('donations/',          views.donation_list,   name='donation_list'),
    path('donations/record/',   views.donation_create, name='donation_create'),

    # ── Phase 3 & 26: Donor self-submission & Make Donation ───────────────
    path('donations/make/',     views.make_donation,         name='make_donation'),
    path('donations/submit/',   views.donor_submit_donation, name='donor_submit_donation'),

    # ── Phase 3: Verification queue (Admin + Member) ──────────────────────
    path('donations/pending/',  views.pending_donation_list, name='pending_donations'),

    # ── Phase 3 & 27: Admin verify/review a specific donation ─────────────
    path('donations/<int:pk>/verify/', views.verify_donation, name='verify_donation'),
    path('donations/<int:pk>/review/', views.verify_donation, name='review_donation'),

    # ── Phase 46: Donor Print Receipt ──────────────────────────────────────
    path('donations/<int:donation_id>/receipt/', views.donor_receipt_view, name='receipt_print'),
]
