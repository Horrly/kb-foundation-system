from django.urls import path
from . import views

app_name = 'expenditures'

urlpatterns = [
    path('',                 views.expenditure_list,   name='expenditure_list'),
    path('add/',             views.expenditure_create, name='expenditure_create'),
    path('<int:pk>/edit/',   views.expenditure_update, name='expenditure_update'),
    path('<int:pk>/delete/', views.expenditure_delete, name='expenditure_delete'),
]
