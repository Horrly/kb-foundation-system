"""
accounts/admin.py  — Phase 1 update
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Extended UserAdmin to display and manage all KB Foundation custom fields."""

    # ── List view ─────────────────────────────────────────────────────────────
    list_display  = (
        'username', 'email', 'first_name', 'last_name',
        'role', 'unique_id', 'requires_password_change',
        'is_staff', 'is_active',
    )
    list_filter   = ('role', 'requires_password_change', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'unique_id')
    ordering      = ('username',)

    # ── Detail / edit view ────────────────────────────────────────────────────
    fieldsets = UserAdmin.fieldsets + (
        ('KB Foundation — Role & Access', {
            'fields': ('role', 'unique_id', 'requires_password_change'),
            'description': (
                '"Unique ID" is auto-generated on first save. '
                'Tick "Requires Password Change" when provisioning accounts on behalf of users.'
            ),
        }),
    )

    # ── Add-user form ─────────────────────────────────────────────────────────
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('KB Foundation — Role & Access', {
            'fields': ('role', 'requires_password_change'),
        }),
    )

    # ── Make unique_id read-only in the edit form (set automatically) ─────────
    readonly_fields = ('unique_id',)
