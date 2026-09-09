"""
accounts/models.py

CustomUser model — Phase 1 update adds:
  - DONOR role (donors now have login access)
  - unique_id (system-assigned reference ID)
  - requires_password_change (flag for first-login enforcement)
"""

import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    """
    Extended user model for KB Foundation.

    CRITICAL: AUTH_USER_MODEL = 'accounts.CustomUser' must be set in
    settings.py BEFORE the very first `makemigrations` run.
    """

    class Role(models.TextChoices):
        ADMIN     = 'admin',     'Admin'
        MEMBER    = 'member',    'Member'
        REVIEWER  = 'reviewer',  'Reviewer'
        APPLICANT = 'applicant', 'Applicant'
        DONOR     = 'donor',     'Donor'      # Phase 1: Donors now have portal access

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.APPLICANT,
        help_text='Determines what areas of the system this user can access.',
    )


    class CommitteeRole(models.TextChoices):
        STANDARD  = 'standard',  'Standard Member'
        TREASURER = 'treasurer', 'Treasurer'
        WELFARE   = 'welfare',   'Welfare'
        SECRETARY = 'secretary', 'Secretary'

    committee_role = models.CharField(
        max_length=20,
        choices=CommitteeRole.choices,
        default=CommitteeRole.STANDARD,
        help_text='Only applicable if the user is a Member.',
    )

    # Phase 1 additions -------------------------------------------------------

    unique_id = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        verbose_name='Unique Reference ID',
        help_text=(
            'System-assigned reference ID, e.g. KBD-0001 for donors, '
            'KBA-0001 for applicants. Auto-generated on save if blank.'
        ),
    )

    requires_password_change = models.BooleanField(
        default=False,
        verbose_name='Requires Password Change',
        help_text=(
            'If True, user is redirected to change their password on next login. '
            'Set to True when an admin creates an account on behalf of a user.'
        ),
    )

    # ── Standard fields ───────────────────────────────────────────────────────

    # Make email required and unique
    email = models.EmailField(unique=True)

    # ── Auto-generate unique_id on save ───────────────────────────────────────
    def _generate_unique_id(self):
        """
        Generate a human-readable reference ID based on the user's role.
        Format: KB<role-prefix>-<4-digit-padded-pk>
        Examples: KBD-0001 (Donor), KBA-0042 (Applicant), KBM-0005 (Member)
        """
        prefix_map = {
            self.Role.ADMIN:     'KBX',
            self.Role.MEMBER:    'KBM',
            self.Role.REVIEWER:  'KBR',
            self.Role.APPLICANT: 'KBA',
            self.Role.DONOR:     'KBD',
        }
        prefix = prefix_map.get(self.role, 'KBU')
        return f'{prefix}-{self.pk:04d}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Assign unique_id after PK is available
        if not self.unique_id:
            self.unique_id = self._generate_unique_id()
            # Use update() to avoid recursion
            CustomUser.objects.filter(pk=self.pk).update(unique_id=self.unique_id)

    # ── Convenience properties ────────────────────────────────────────────────
    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_member(self):
        return self.role == self.Role.MEMBER

    @property
    def is_reviewer(self):
        return self.role == self.Role.REVIEWER

    @property
    def is_applicant(self):
        return self.role == self.Role.APPLICANT

    @property
    def is_donor(self):
        return self.role == self.Role.DONOR

    def __str__(self):
        uid = f' [{self.unique_id}]' if self.unique_id else ''
        return f'{self.username} ({self.get_role_display()}){uid}'

    class Meta:
        verbose_name        = 'User'
        verbose_name_plural = 'Users'
        ordering            = ['username']
