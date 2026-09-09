from django.urls import path
from . import views

app_name = 'scholarships'

urlpatterns = [
    # ── Applicant-facing ──────────────────────────────────────────────────
    path('apply/',           views.application_create,      name='application_create'),
    path('my-application/',  views.application_status,      name='application_status'),
    path('upload-document/', views.document_upload,         name='document_upload'),
    path('submit/',          views.application_submit,      name='application_submit'),

    # ── Staff-facing ──────────────────────────────────────────────────────
    path('',                        views.application_list,         name='application_list'),
    path('<int:pk>/',               views.application_detail_staff, name='application_detail_staff'),
    path('<int:pk>/review/',        views.application_review,       name='application_review'),
    path('<int:pk>/member-recommend/', views.member_recommend,      name='member_recommend'),
    path('<int:pk>/admin-decision/',   views.admin_decision,        name='admin_decision'),
    path('<int:pk>/award/',         views.award_scholarship,        name='award_scholarship'),
    path('<int:pk>/disburse/',      views.disburse_scholarship,     name='disburse_scholarship'),
]
