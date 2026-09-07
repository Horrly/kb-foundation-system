"""
accounts/backends.py  — Phase 2.5

Custom authentication backend that lets users log in with any of:
  - Their email address        (all roles)
  - Their unique_id            (KBD-0001, KBM-0003, etc.)
  - Their standard username    (fallback / applicants / admins)

Registered in settings.py via AUTHENTICATION_BACKENDS.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


UserModel = get_user_model()


class EmailOrUniqueIdModelBackend(ModelBackend):
    """
    A superset of Django's default ModelBackend.

    authenticate() is overridden to resolve the incoming `username`
    credential against THREE columns in a single database query:
        1. username   (standard Django field — all users)
        2. email      (unique per user — preferred for Applicants/Admins)
        3. unique_id  (system-assigned ref ID — preferred for Donors/Members)

    Password verification and user-can-authenticate checks are
    delegated to the parent ModelBackend so we stay in sync with
    Django's built-in logic (inactive users are rejected, etc.).
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        Attempt to find and authenticate a user by username, email, or unique_id.

        Args:
            request:  The current HttpRequest (may be None in shell usage).
            username: The value entered in the login credential field.
                      Despite the parameter name, it may contain any of the
                      three identifier types.
            password: The plain-text password to verify.

        Returns:
            The authenticated CustomUser instance, or None.
        """
        if username is None or password is None:
            return None

        identifier = username.strip()

        # ── Single query across all three identifier columns ──────────────────
        # email__iexact  → case-insensitive email comparison
        # unique_id__iexact → case-insensitive match (KBD-0001 == kbd-0001)
        # username       → exact match (Django default behaviour)
        try:
            user = UserModel.objects.get(
                Q(username=identifier)
                | Q(email__iexact=identifier)
                | Q(unique_id__iexact=identifier)
            )
        except UserModel.DoesNotExist:
            # Run the default password hasher to mitigate timing attacks
            # (same technique Django's own ModelBackend uses)
            UserModel().set_password(password)
            return None
        except UserModel.MultipleObjectsReturned:
            # Theoretically impossible because email and unique_id are both
            # unique fields, but handle defensively.
            return None

        # ── Verify password and check is_active ───────────────────────────────
        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None

    def get_user(self, user_id):
        """Standard pk-based user retrieval (required by Django's auth framework)."""
        try:
            user = UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
        return user if self.user_can_authenticate(user) else None
