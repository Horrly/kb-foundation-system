"""
accounts/middleware.py

ForcePasswordChangeMiddleware — Phase 2

Intercepts every authenticated request and redirects the user to the
password change page if their `requires_password_change` flag is True.

Registration in settings.py MIDDLEWARE list (add AFTER AuthenticationMiddleware):

    'accounts.middleware.ForcePasswordChangeMiddleware',

Exempt URLs (to prevent infinite redirect loops):
  - The password change page itself
  - The logout URL (so users can always escape)
  - Django Admin URLs (admins bypass via is_staff check)
  - Static / media file URLs
"""

from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse, resolve, Resolver404


# URLs that must always be accessible regardless of password-change status
_ALWAYS_ALLOWED_URL_NAMES = {
    'accounts:force_password_change',
    'accounts:logout',
    'accounts:login',         # Standard portal — always reachable
    'accounts:portal_login',  # Staff/Donor portal — always reachable
}

# URL path prefixes that are always exempt (static, media, admin)
_EXEMPT_PREFIXES = (
    '/admin/',
    settings.STATIC_URL,
    settings.MEDIA_URL,
)


class ForcePasswordChangeMiddleware:
    """
    WSGI middleware that redirects users who must change their password.

    Placed after AuthenticationMiddleware in the MIDDLEWARE list so that
    request.user is always populated before this middleware runs.
    """

    def __init__(self, get_response):
        self.get_response     = get_response
        # Resolve the password-change URL once at startup for efficiency
        self._change_url_path = reverse('accounts:force_password_change')

    def __call__(self, request):
        # ── Fast exits ────────────────────────────────────────────────────────

        # 1. Anonymous users — nothing to enforce
        if not request.user.is_authenticated:
            return self.get_response(request)

        # 2. Superusers and is_staff bypass the forced change
        #    (Django Admin users set their own passwords)
        if request.user.is_superuser or request.user.is_staff:
            return self.get_response(request)

        # 3. No flag set — normal flow
        if not getattr(request.user, 'requires_password_change', False):
            return self.get_response(request)

        # ── Exempt URL checks ─────────────────────────────────────────────────

        current_path = request.path_info

        # 4. Static / media / admin prefixes are always exempt
        if current_path.startswith(_EXEMPT_PREFIXES):
            return self.get_response(request)

        # 5. Already on the password change or logout URL → let through
        try:
            match = resolve(current_path)
            full_name = f'{match.app_name}:{match.url_name}' if match.app_name else match.url_name
            if full_name in _ALWAYS_ALLOWED_URL_NAMES:
                return self.get_response(request)
        except Resolver404:
            pass  # Unknown URL — fall through to the redirect

        # ── Redirect ──────────────────────────────────────────────────────────

        # Preserve ?next= so we can bounce back after the change is done
        # (force_password_change view currently redirects to dashboard,
        #  but this keeps the option open for future enhancements)
        return redirect(self._change_url_path)
