"""
expenditures/filters.py

ExpenditureFilter using django-filter.
Supports: title search, category, date range.
"""

import django_filters
from django import forms
from .models import Expenditure


class ExpenditureFilter(django_filters.FilterSet):

    # Free-text title search
    title = django_filters.CharFilter(
        lookup_expr='icontains',
        label='Search Title',
        widget=forms.TextInput(attrs={
            'class':       'form-control',
            'placeholder': 'Search by title or description…',
            'id':          'id_filter_exp_title',
        }),
    )

    # Category dropdown — empty label shows all
    category = django_filters.ChoiceFilter(
        choices=[('', 'All Categories')] + list(Expenditure.Category.choices),
        label='Category',
        empty_label=None,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id':    'id_filter_exp_category',
        }),
    )

    # Date range
    date_from = django_filters.DateFilter(
        field_name='date',
        lookup_expr='gte',
        label='Date From',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type':  'date',
            'id':    'id_filter_exp_date_from',
        }),
    )

    date_to = django_filters.DateFilter(
        field_name='date',
        lookup_expr='lte',
        label='Date To',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type':  'date',
            'id':    'id_filter_exp_date_to',
        }),
    )

    class Meta:
        model  = Expenditure
        fields = ['title', 'category', 'date_from', 'date_to']
