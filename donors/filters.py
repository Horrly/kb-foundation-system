"""
donors/filters.py

django-filter FilterSets for Donor and Donation search/filtering.
"""

import django_filters
from django import forms
from .models import Donor, Donation


class DonorFilter(django_filters.FilterSet):
    """
    Allows searching donors by name or email (case-insensitive contains).
    Used in DonorListView.
    """

    search = django_filters.CharFilter(
        method='filter_search',
        label='Search',
        widget=forms.TextInput(attrs={
            'class':       'form-control',
            'placeholder': 'Search by name or email…',
            'id':          'id_donor_search',
        }),
    )

    def filter_search(self, queryset, name, value):
        """Filter across full_name AND email in a single search box."""
        from django.db.models import Q
        return queryset.filter(
            Q(full_name__icontains=value) | Q(email__icontains=value)
        )

    class Meta:
        model  = Donor
        fields = ['search']


# ---------------------------------------------------------------------------

class DonationFilter(django_filters.FilterSet):
    """
    Allows filtering donations by donor, date range, and payment method.
    Used in DonationListView.
    """

    donor = django_filters.ModelChoiceFilter(
        queryset=Donor.objects.all(),
        label='Donor',
        empty_label='All Donors',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id':    'id_filter_donor',
        }),
    )

    date_from = django_filters.DateFilter(
        field_name='date',
        lookup_expr='gte',
        label='Date From',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type':  'date',
            'id':    'id_filter_date_from',
        }),
    )

    date_to = django_filters.DateFilter(
        field_name='date',
        lookup_expr='lte',
        label='Date To',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type':  'date',
            'id':    'id_filter_date_to',
        }),
    )

    payment_method = django_filters.ChoiceFilter(
        choices=[('', 'All Methods')] + list(Donation.PaymentMethod.choices),
        label='Payment Method',
        empty_label=None,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id':    'id_filter_payment',
        }),
    )

    class Meta:
        model  = Donation
        fields = ['donor', 'date_from', 'date_to', 'payment_method']
