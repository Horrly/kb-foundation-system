"""
accounts/management/commands/setup_roles.py

Management command to create the four KB Foundation Django Groups
and assign meaningful permissions to each.

Usage:
    python manage.py setup_roles

Run this ONCE after your first `migrate`, or whenever you set up
the project on a new machine. It is idempotent — safe to run multiple times.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


class Command(BaseCommand):
    help = (
        'Creates the four KB Foundation RBAC Groups (Admin, Member, Reviewer, Applicant) '
        'and assigns the appropriate Django permissions to each group.'
    )

    # ------------------------------------------------------------------
    # Permission sets — list of (app_label, model, codename_suffix) tuples
    # Suffixes follow Django convention: add, change, delete, view
    # ------------------------------------------------------------------
    ROLE_PERMISSIONS = {
        'Admin': [
            # Full access to everything — we add_all deliberately;
            # the Admin group typically also has is_staff = True set via admin.
            ('donors',       'donor',                'add'),
            ('donors',       'donor',                'change'),
            ('donors',       'donor',                'delete'),
            ('donors',       'donor',                'view'),
            ('donors',       'donation',             'add'),
            ('donors',       'donation',             'change'),
            ('donors',       'donation',             'delete'),
            ('donors',       'donation',             'view'),
            ('expenditures', 'expenditure',          'add'),
            ('expenditures', 'expenditure',          'change'),
            ('expenditures', 'expenditure',          'delete'),
            ('expenditures', 'expenditure',          'view'),
            ('scholarships', 'scholarshipapplication','add'),
            ('scholarships', 'scholarshipapplication','change'),
            ('scholarships', 'scholarshipapplication','delete'),
            ('scholarships', 'scholarshipapplication','view'),
            ('scholarships', 'document',             'add'),
            ('scholarships', 'document',             'change'),
            ('scholarships', 'document',             'delete'),
            ('scholarships', 'document',             'view'),
            ('scholarships', 'scholarshiprecipient', 'add'),
            ('scholarships', 'scholarshiprecipient', 'change'),
            ('scholarships', 'scholarshiprecipient', 'delete'),
            ('scholarships', 'scholarshiprecipient', 'view'),
            ('accounts',     'customuser',           'add'),
            ('accounts',     'customuser',           'change'),
            ('accounts',     'customuser',           'delete'),
            ('accounts',     'customuser',           'view'),
        ],
        'Member': [
            # Read/write on donors, donations, expenditures; view-only on scholarships
            ('donors',       'donor',                'add'),
            ('donors',       'donor',                'change'),
            ('donors',       'donor',                'view'),
            ('donors',       'donation',             'add'),
            ('donors',       'donation',             'change'),
            ('donors',       'donation',             'view'),
            ('expenditures', 'expenditure',          'add'),
            ('expenditures', 'expenditure',          'change'),
            ('expenditures', 'expenditure',          'view'),
            ('scholarships', 'scholarshipapplication','view'),
            ('scholarships', 'scholarshiprecipient', 'view'),
        ],
        'Reviewer': [
            # Can view and change application status; cannot add or delete
            ('scholarships', 'scholarshipapplication','view'),
            ('scholarships', 'scholarshipapplication','change'),
            ('scholarships', 'document',             'view'),
            ('scholarships', 'scholarshiprecipient', 'view'),
        ],
        'Applicant': [
            # Can only manage their own application and documents (view enforced in views)
            ('scholarships', 'scholarshipapplication','add'),
            ('scholarships', 'scholarshipapplication','change'),
            ('scholarships', 'scholarshipapplication','view'),
            ('scholarships', 'document',             'add'),
            ('scholarships', 'document',             'view'),
        ],
        'Donor': [
            # Can view their own donor profile and donation history (object-level enforced in views)
            ('donors', 'donor',    'view'),
            ('donors', 'donation', 'view'),
        ],
    }

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== KB Foundation RBAC Setup ===\n'))

        created_count  = 0
        existing_count = 0

        for group_name, perm_list in self.ROLE_PERMISSIONS.items():
            group, created = Group.objects.get_or_create(name=group_name)

            if created:
                created_count += 1
                self.stdout.write(f'  {self.style.SUCCESS("CREATED")} group: {group_name}')
            else:
                existing_count += 1
                self.stdout.write(f'  {self.style.WARNING("EXISTS ")} group: {group_name} — refreshing permissions')

            # Assign permissions (skip gracefully if model doesn't exist yet)
            assigned = []
            skipped  = []

            for app_label, model_name, action in perm_list:
                codename = f'{action}_{model_name}'
                try:
                    perm = Permission.objects.get(
                        content_type__app_label=app_label,
                        codename=codename,
                    )
                    group.permissions.add(perm)
                    assigned.append(codename)
                except Permission.DoesNotExist:
                    skipped.append(f'{app_label}.{codename}')

            if assigned:
                self.stdout.write(f'    [OK] Assigned {len(assigned)} permission(s).')
            if skipped:
                self.stdout.write(
                    f'    {self.style.WARNING("[WARN]")} {len(skipped)} permission(s) '
                    f'(models may not be migrated yet): {", ".join(skipped)}'
                )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'Done. {created_count} group(s) created, {existing_count} group(s) already existed.'
        ))
        self.stdout.write(
            self.style.NOTICE(
                'Tip: Re-run this command after each new app migration to assign any skipped permissions.\n'
            )
        )
