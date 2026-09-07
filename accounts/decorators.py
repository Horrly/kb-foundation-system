"""
accounts/decorators.py

Role-based access control decorators.
Usage:
    @login_required
    @role_required('admin', 'member')
    def my_view(request):
        ...
"""

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def role_required(*roles):
    """
    Restrict a view to users whose role is in the given list.

    Args:
        *roles: One or more role strings from CustomUser.Role choices
                e.g. 'admin', 'member', 'reviewer', 'applicant'

    Redirects unauthenticated users to LOGIN_URL.
    Redirects authenticated users with wrong role to their dashboard
    with a permission-denied message.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Must be logged in first
            if not request.user.is_authenticated:
                return redirect('accounts:login')

            # Superusers bypass all role checks
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # Check if user's role is in the allowed roles list
            if request.user.role not in roles:
                messages.error(
                    request,
                    "You do not have permission to access that page."
                )
                return redirect('reports:dashboard')

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
