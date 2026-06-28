"""
accounts/permissions.py
-----------------------
Reusable DRF permission classes for role-based access control.
Uses Django's built-in Group/Permission system via ModelBackend.

Usage
-----
# Check a specific permission codename:
    from accounts.permissions import require_permission
    from accounts.constants import PERM_USER_VIEW

    class MyView(APIView):
        permission_classes = [IsAuthenticated, require_permission(PERM_USER_VIEW)]

# Restrict to specific role/group names:
    from accounts.permissions import require_roles
    from accounts.constants import ROLE_ADMIN, ROLE_SUPER_ADMIN

    class AdminOnlyView(APIView):
        permission_classes = [IsAuthenticated, require_roles(ROLE_ADMIN, ROLE_SUPER_ADMIN)]

Notes
-----
- Superusers (is_superuser=True) automatically bypass ALL permission checks
  via Django's ModelBackend — no special-casing needed here.
- Group permissions are resolved by Django's ModelBackend (default backend).
  No DB query is made per-request after the first check; Django caches the
  full permission set on the user object for the lifetime of the request.
- Add a permission to a Group in Django Admin or via a fixture to grant access.
"""

from rest_framework.permissions import BasePermission


class HasRolePermission(BasePermission):
    """
    Checks whether the authenticated user has a specific permission codename
    via their assigned Group using Django's standard has_perm() check.

    Superusers bypass this check automatically (Django ModelBackend behaviour).

    Override `permission_codename` in a subclass, or use the
    `require_permission()` factory function instead.
    """

    permission_codename = None  # Override in subclass or use factory

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # Allow view to declare its own codename via `required_permission` attr
        codename = getattr(view, 'required_permission', None) or self.permission_codename
        if not codename:
            return False

        # has_perm handles superuser bypass and group permission lookup.
        # Format: 'app_label.codename'
        return user.has_perm(f'accounts.{codename}')


def require_permission(codename):
    """
    Factory function — returns a DRF permission class that checks for a
    specific permission codename.

    Example:
        permission_classes = [IsAuthenticated, require_permission('user_view')]

    Args:
        codename (str): A permission codename, e.g. 'user_view'.

    Returns:
        type: A BasePermission subclass.
    """
    class _Permission(HasRolePermission):
        permission_codename = codename

    _Permission.__name__ = f"Has_{codename}_Permission"
    _Permission.__qualname__ = _Permission.__name__
    return _Permission


class IsRole(BasePermission):
    """
    Allows access only to users whose Group name is in `allowed_role_names`.

    Override `allowed_role_names` in a subclass, or use the
    `require_roles()` factory function instead.

    NOTE: Unlike require_permission(), this does NOT automatically bypass for
    superusers. Include ROLE_SUPER_ADMIN in the list if superusers should have
    access, or rely solely on require_permission() for superuser-safe checks.
    """

    allowed_role_names = ()

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return user.groups.filter(name__in=self.allowed_role_names).exists()


def require_roles(*role_names):
    """
    Factory function — returns a DRF permission class that allows access
    only to users whose Group name is in the provided list.

    Example:
        from accounts.constants import ROLE_ADMIN, ROLE_SUPER_ADMIN
        permission_classes = [IsAuthenticated, require_roles(ROLE_ADMIN, ROLE_SUPER_ADMIN)]

    Args:
        *role_names (str): One or more Group name strings from constants.py.

    Returns:
        type: A BasePermission subclass.
    """
    class _RolePermission(IsRole):
        allowed_role_names = role_names

    role_label = "_or_".join(str(r).replace(' ', '_') for r in role_names)
    _RolePermission.__name__ = f"IsRole_{role_label}"
    _RolePermission.__qualname__ = _RolePermission.__name__
    return _RolePermission
