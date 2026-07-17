from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


User = get_user_model()


class EmailLoginBackend(ModelBackend):
    """
    Authenticates users by email (case-insensitive) and password.

    Returns the user regardless of is_active — the login view decides how to
    respond to inactive accounts.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None
        user = User.objects.filter(email__iexact=username).first()
        if user and user.check_password(password):
            return user
        return None
