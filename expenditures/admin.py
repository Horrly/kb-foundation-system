"""
expenditures/admin.py
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import Expenditure


@admin.register(Expenditure)
class ExpenditureAdmin(admin.ModelAdmin):
    list_display   = (
        'title', 'category_display', 'amount_display',
        'date', 'recorded_by', 'receipt_link', 'created_at',
    )
    list_filter    = ('category', 'date')
    search_fields  = ('title', 'notes', 'recorded_by')
    date_hierarchy = 'date'
    readonly_fields = ('created_at', 'updated_at', 'recorded_by')
    ordering       = ('-date',)

    fieldsets = (
        ('Expenditure Details', {
            'fields': ('title', 'category', 'amount', 'date'),
        }),
        ('Receipt & Notes', {
            'fields': ('receipt', 'notes'),
        }),
        ('System', {
            'fields': ('recorded_by', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Category')
    def category_display(self, obj):
        colour_map = {
            'scholarship_grants': '#1a3d5c',
            'administrative':     '#6c757d',
            'events':             '#0d6efd',
            'marketing':          '#e8a020',
            'logistics':          '#198754',
            'other':              '#adb5bd',
        }
        colour = colour_map.get(obj.category, '#adb5bd')
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:12px;font-size:.78rem;">{}</span>',
            colour,
            obj.get_category_display(),
        )

    @admin.display(description='Amount (₦)')
    def amount_display(self, obj):
        return format_html('<strong>₦{:,}</strong>', obj.amount)

    @admin.display(description='Receipt')
    def receipt_link(self, obj):
        if obj.receipt:
            return format_html(
                '<a href="{}" target="_blank" title="View receipt">'
                '<span style="color:green">&#10003; View</span></a>',
                obj.receipt.url,
            )
        return format_html('<span style="color:#ccc;">None</span>')
