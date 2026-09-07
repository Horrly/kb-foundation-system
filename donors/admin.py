"""
donors/admin.py  — Phase 3 update

Adds status filter, receipt link, verification fields, and
colour-coded status display to DonationAdmin.
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import Donor, Donation


# ── Inline ────────────────────────────────────────────────────────────────────

class DonationInline(admin.TabularInline):
    model            = Donation
    extra            = 0
    fields           = ('date', 'amount', 'payment_method', 'status', 'amount_confirmed')
    readonly_fields  = ('status', 'amount_confirmed')
    ordering         = ('-date',)
    show_change_link = True


# ── Donor Admin ───────────────────────────────────────────────────────────────

@admin.register(Donor)
class DonorAdmin(admin.ModelAdmin):
    list_display    = ('full_name', 'email', 'phone', 'user',
                       'donation_count_display', 'total_donated_display', 'created_at')
    list_filter     = ('created_at',)
    search_fields   = ('full_name', 'email', 'phone', 'user__username', 'user__unique_id')
    readonly_fields = ('created_at', 'updated_at')
    inlines         = [DonationInline]
    ordering        = ('-created_at',)

    fieldsets = (
        ('Personal Information', {
            'fields': ('full_name', 'email', 'phone', 'address'),
        }),
        ('Portal Account', {
            'fields': ('user',),
            'description': 'Link to this donor\'s CustomUser portal account.',
        }),
        ('Internal Notes', {
            'fields': ('notes',),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Donations')
    def donation_count_display(self, obj):
        return obj.donation_count()

    @admin.display(description='Confirmed Total (₦)')
    def total_donated_display(self, obj):
        return f'\u20a6{obj.total_donated():,.2f}'


# ── Donation Admin ────────────────────────────────────────────────────────────

@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display   = (
        'donor', 'amount', 'date', 'payment_method',
        'reference_number', 'status_badge', 'amount_confirmed', 'recorded_at',
    )
    list_filter    = ('status', 'payment_method', 'date')
    search_fields  = ('donor__full_name', 'donor__email', 'reference_number')
    date_hierarchy = 'date'
    ordering       = ('-date',)
    readonly_fields = ('recorded_at', 'reviewed_at', 'receipt_preview')

    fieldsets = (
        ('Donation Details', {
            'fields': ('donor', 'amount', 'date', 'payment_method', 'reference_number', 'notes'),
        }),
        ('Receipt', {
            'fields': ('receipt', 'receipt_preview'),
        }),
        ('Verification', {
            'fields': ('status', 'amount_confirmed', 'admin_notes', 'reviewed_at'),
            'description': (
                'Set status to "confirmed" and enter the actual bank amount, '
                'or "rejected" and enter the reason.'
            ),
        }),
        ('System', {
            'fields': ('recorded_at',),
            'classes': ('collapse',),
        }),
    )

    # ── Custom display columns ────────────────────────────────────────────────

    @admin.display(description='Status')
    def status_badge(self, obj):
        colours = {
            'pending':   ('#856404', '#fff3cd'),
            'confirmed': ('#0a3622', '#d1e7dd'),
            'rejected':  ('#842029', '#f8d7da'),
        }
        fg, bg = colours.get(obj.status, ('#333', '#eee'))
        return format_html(
            '<span style="background:{};color:{};padding:2px 10px;'
            'border-radius:12px;font-size:.78rem;font-weight:600;">{}</span>',
            bg, fg, obj.get_status_display(),
        )

    @admin.display(description='Receipt Preview')
    def receipt_preview(self, obj):
        if not obj.receipt:
            return '—'
        url  = obj.receipt.url
        name = obj.receipt.name.split('/')[-1]
        if name.lower().endswith('.pdf'):
            return format_html(
                '<a href="{}" target="_blank">'
                '<i class="fas fa-file-pdf"></i> View PDF: {}</a>', url, name
            )
        return format_html(
            '<a href="{}" target="_blank">'
            '<img src="{}" style="max-height:120px;border:1px solid #dee2e6;'
            'border-radius:4px;"></a>', url, url
        )
