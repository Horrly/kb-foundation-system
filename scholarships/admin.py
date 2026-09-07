"""
scholarships/admin.py
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import ScholarshipApplication, Document, ScholarshipRecipient


# ── Inlines ──────────────────────────────────────────────────────────────────

class DocumentInline(admin.TabularInline):
    model            = Document
    extra            = 0
    fields           = ('document_type', 'file', 'uploaded_at')
    readonly_fields  = ('uploaded_at',)
    show_change_link = True


class ScholarshipRecipientInline(admin.StackedInline):
    model           = ScholarshipRecipient
    extra           = 0
    fields          = ('awarded_date', 'amount_awarded', 'notes')
    can_delete      = False
    verbose_name_plural = 'Recipient Record (set on approval)'


# ── ScholarshipApplication ───────────────────────────────────────────────────

@admin.register(ScholarshipApplication)
class ScholarshipApplicationAdmin(admin.ModelAdmin):
    list_display   = (
        'applicant_name', 'institution', 'academic_session',
        'current_cgpa', 'status_badge', 'application_date',
        'document_count', 'created_at',
    )
    list_filter    = ('status', 'academic_session', 'application_date')
    search_fields  = (
        'applicant__username', 'applicant__first_name', 'applicant__last_name',
        'applicant__email', 'institution', 'course_of_study',
    )
    date_hierarchy  = 'application_date'
    readonly_fields = ('created_at', 'updated_at', 'application_date')
    inlines         = [DocumentInline, ScholarshipRecipientInline]
    ordering        = ('-application_date',)
    list_per_page   = 25

    fieldsets = (
        ('Applicant', {
            'fields': ('applicant', 'academic_session'),
        }),
        ('Academic Details', {
            'fields': ('institution', 'course_of_study', 'level', 'current_cgpa'),
        }),
        ('Statement of Purpose', {
            'fields': ('statement_of_purpose',),
            'classes': ('collapse',),
        }),
        ('Review', {
            'fields': ('status', 'reviewer_notes'),
        }),
        ('Timestamps', {
            'fields': ('application_date', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Applicant', ordering='applicant__first_name')
    def applicant_name(self, obj):
        return obj.applicant.get_full_name() or obj.applicant.username

    @admin.display(description='Status')
    def status_badge(self, obj):
        colours = {
            'pending':      ('#ffc107', '#000'),
            'under_review': ('#0dcaf0', '#000'),
            'approved':     ('#198754', '#fff'),
            'rejected':     ('#dc3545', '#fff'),
        }
        bg, fg = colours.get(obj.status, ('#adb5bd', '#000'))
        return format_html(
            '<span style="background:{};color:{};padding:3px 10px;'
            'border-radius:12px;font-size:.78rem;font-weight:600;">{}</span>',
            bg, fg, obj.get_status_display(),
        )

    @admin.display(description='Docs')
    def document_count(self, obj):
        count = obj.documents.count()
        colour = 'green' if count >= 3 else 'orange' if count > 0 else 'red'
        return format_html(
            '<span style="color:{}; font-weight:600;">{}</span>', colour, count
        )


# ── Document ─────────────────────────────────────────────────────────────────

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display   = ('get_applicant', 'document_type', 'filename_link', 'uploaded_at')
    list_filter    = ('document_type', 'uploaded_at')
    search_fields  = ('application__applicant__username', 'application__applicant__email')
    readonly_fields = ('uploaded_at',)

    @admin.display(description='Applicant')
    def get_applicant(self, obj):
        return obj.application.applicant.get_full_name() or obj.application.applicant.username

    @admin.display(description='File')
    def filename_link(self, obj):
        if obj.file:
            return format_html(
                '<a href="{}" target="_blank">{}</a>',
                obj.file.url, obj.filename()
            )
        return '—'


# ── ScholarshipRecipient ─────────────────────────────────────────────────────

@admin.register(ScholarshipRecipient)
class ScholarshipRecipientAdmin(admin.ModelAdmin):
    list_display   = ('get_recipient_name', 'get_institution', 'amount_awarded', 'awarded_date')
    list_filter    = ('awarded_date',)
    search_fields  = (
        'application__applicant__username',
        'application__applicant__first_name',
        'application__institution',
    )
    readonly_fields = ('created_at',)

    @admin.display(description='Recipient', ordering='application__applicant__first_name')
    def get_recipient_name(self, obj):
        u = obj.application.applicant
        return u.get_full_name() or u.username

    @admin.display(description='Institution')
    def get_institution(self, obj):
        return obj.application.institution
