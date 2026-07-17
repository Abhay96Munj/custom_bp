import logging

from django.contrib.auth import authenticate
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.utils import timezone
from rest_framework import generics, mixins, permissions, status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView, exception_handler
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from core.base_classes import BaseModelViewSet
from .constants import ROLE_ADMIN, ROLE_SUPER_ADMIN, PERM_ROLE_MANAGE
from .models import State, User, Address, Country
from .permissions import require_permission, require_roles
from .serializers import (
    UserSerializer,
    RoleSerializer,
    CountryStateSerializer,
    ProfileSerializer,
    StateSerializer,
    AddressSerializer,
    LoginSerializer,
    VerifyOtpSerializer,
    ForgotPasswordRequestOtpSerializer,
    ResetPasswordSerializer,
    ChangePasswordSerializer,
    AdminAddUserSerializer,
)
from .services.otp_service import OtpService, PURPOSE_SIGNUP, PURPOSE_PASSWORD_RESET
from .utils import SignupEmailSender, ForgotPasswordEmailSender

logger = logging.getLogger(__name__)

# Login lockout: after LOGIN_MAX_ATTEMPTS failures within LOGIN_LOCKOUT_SECONDS,
# further attempts for that email are rejected until the window expires.
LOGIN_MAX_ATTEMPTS = 5
LOGIN_LOCKOUT_SECONDS = 15 * 60


def _login_fail_key(email):
    return f"login-fail:{email.strip().lower()}"


def _login_lock_key(email):
    return f"login-lock:{email.strip().lower()}"


def clear_login_lockout(email):
    cache.delete_many([_login_fail_key(email), _login_lock_key(email)])


def custom_exception_handler(exc, context):
    """
    Wraps every DRF error response in the standard envelope, logs it, and
    keeps the full error detail alongside a single human-readable message.

    Response shape:
        {
            "success": false,
            "status": <http status>,
            "message": "<first error message>",
            "errors": <full DRF error detail, per field>,
            "data": {}
        }
    """

    response = exception_handler(exc, context)
    if response is None:
        return None

    errors = response.data
    message = None
    error_field = None

    if isinstance(errors, dict):
        for field, field_errors in errors.items():
            if isinstance(field_errors, list) and len(field_errors) > 0:
                message = str(field_errors[0])
                error_field = field
                break
            elif isinstance(field_errors, str):
                message = str(field_errors)
                error_field = field
                break
        if not message:
            message = str(errors.get("detail", "An error occurred."))
    elif isinstance(errors, list):
        message = str(errors[0]) if errors else "An error occurred."
    else:
        message = str(errors)

    view = context.get("view")
    request = context.get("request")
    logger.warning(
        "API error (%s) in %s [%s]: %s",
        response.status_code,
        view.__class__.__name__ if view else "unknown view",
        request.get_full_path() if request else "unknown path",
        errors,
    )

    response.data = {
        "success": False,
        "status": response.status_code,
        "message": message,
        "errors": errors,
        "data": {},
    }
    if error_field:
        response.data["error_field"] = error_field
    return response


class CustomTokenRefreshView(TokenRefreshView):
    """
    Handles refresh Token and updates the user's last login.

    Returns:
        Response: the new access (and rotated refresh) token in the standard
        response envelope.
    """

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        if response.status_code == status.HTTP_200_OK:
            # Best-effort last_login update; never fail a successful refresh.
            try:
                access_token = response.data.get("access")
                if access_token:
                    token = AccessToken(access_token)
                    User.objects.filter(id=token["user_id"]).update(
                        last_login=timezone.now()
                    )
            except Exception:
                logger.exception("Failed to update last_login on token refresh")

            response.data = {
                "success": True,
                "status": status.HTTP_200_OK,
                "message": "Token refreshed successfully",
                "data": response.data,
            }

        return response


class AdminUserViewSet(BaseModelViewSet):
    """
    Manages admin user operations.
    Restricted to Super Admin and Admin roles only.
    """

    queryset = User.objects.all().order_by("-created_at")
    serializer_class = ProfileSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        require_roles(ROLE_SUPER_ADMIN, ROLE_ADMIN),
    ]


class SignupApiView(APIView):
    """
    Handles user registration and OTP generation.
    """

    permission_classes = (permissions.AllowAny,)
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "otp"

    def post(self, request, *args, **kwargs):
        """
        Processes user signup and sends OTP.
        """
        serializer = UserSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        otp_code = OtpService.generate(user.email, PURPOSE_SIGNUP)
        if not SignupEmailSender(user, otp_code).send_email():
            logger.error("Signup verification email failed for %s", user.email)
            return Response(
                {
                    "success": False,
                    "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "message": "Account created, but the verification email could not be sent. Please try again later.",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info(f"User {user.email} signed up successfully. User ID: {user.id}")
        return Response(
            {
                "success": True,
                "status": status.HTTP_201_CREATED,
                "message": "User created successfully. OTP sent to email.",
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginApiView(APIView):
    """
    Handles user login.

    Validates credentials, enforces a temporary lockout after repeated
    failures, checks account status, and returns JWT tokens on success.
    """

    permission_classes = (permissions.AllowAny,)
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        if cache.get(_login_lock_key(email)):
            return Response(
                {
                    "success": False,
                    "status": status.HTTP_429_TOO_MANY_REQUESTS,
                    "message": "Too many failed login attempts. Please try again later or reset your password.",
                    "data": {},
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        user = authenticate(username=email, password=password)
        if not user:
            failures = (cache.get(_login_fail_key(email)) or 0) + 1
            cache.set(_login_fail_key(email), failures, LOGIN_LOCKOUT_SECONDS)
            if failures >= LOGIN_MAX_ATTEMPTS:
                cache.set(_login_lock_key(email), True, LOGIN_LOCKOUT_SECONDS)
            # Same message whether the email exists or not — no user enumeration.
            return Response(
                {
                    "success": False,
                    "status": status.HTTP_400_BAD_REQUEST,
                    "message": "Invalid email or password.",
                    "data": {},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user.is_active:
            return Response(
                {
                    "success": False,
                    "status": status.HTTP_400_BAD_REQUEST,
                    "message": "Your account is inactive. Please verify your email or contact an admin.",
                    "data": {},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        clear_login_lockout(email)
        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

        logger.info(f"User {user.email} logged in successfully. User ID: {user.id}")

        refresh = RefreshToken.for_user(user)
        data = UserSerializer(user, context={"request": request}).data
        data.update(
            {
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh),
            }
        )

        return Response(
            {
                "success": True,
                "status": status.HTTP_200_OK,
                "message": "Logged In Successfully",
                "data": data,
            },
            status=status.HTTP_200_OK,
        )


class LogOutView(APIView):
    """
    Logs the user out by blacklisting the supplied refresh token.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get("refresh_token")
        if not refresh_token:
            return Response(
                {
                    "success": False,
                    "status": status.HTTP_400_BAD_REQUEST,
                    "message": "refresh_token is required.",
                    "data": {},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            return Response(
                {
                    "success": False,
                    "status": status.HTTP_400_BAD_REQUEST,
                    "message": "Invalid refresh token.",
                    "data": {},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info(
            f"User {request.user.email} logged out successfully. User ID: {request.user.id}"
        )
        return Response(
            {
                "success": True,
                "status": status.HTTP_205_RESET_CONTENT,
                "message": "Logged out Successfully",
                "data": {},
            },
            status=status.HTTP_205_RESET_CONTENT,
        )


class TestingResponse(APIView):
    """
    Tests authentication for users. Returns test response for authenticated users.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        return Response(
            {
                "success": True,
                "status": status.HTTP_200_OK,
                "message": "Hello World",
                "data": {},
            },
            status=status.HTTP_200_OK,
        )


class RoleView(ListAPIView):
    """
    Lists all available user groups (roles).
    Restricted to users with the 'role_manage' permission.
    """

    serializer_class = RoleSerializer
    queryset = Group.objects.all()
    permission_classes = [
        permissions.IsAuthenticated,
        require_permission(PERM_ROLE_MANAGE),
    ]


class VerifyOtpView(APIView):
    """
    Verifies an OTP.

    `type` selects the flow: signup verification (default, consumes the OTP
    and activates the account) or a pre-check for the forgot-password /
    invite-accept flows (does not consume — the same OTP is submitted again
    with the new password).
    """

    permission_classes = (permissions.AllowAny,)
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "otp_verify"

    def post(self, request, *args, **kwargs):
        serializer = VerifyOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        otp = serializer.validated_data["otp"]
        req_type = serializer.validated_data.get("type")

        if req_type in ("forgot-password", "invite-accept"):
            purpose, consume = PURPOSE_PASSWORD_RESET, False
        else:
            purpose, consume = PURPOSE_SIGNUP, True

        if not OtpService.verify(email, purpose, otp, consume=consume):
            return Response(
                {
                    "success": False,
                    "status": status.HTTP_400_BAD_REQUEST,
                    "message": "Invalid or expired OTP.",
                    "data": {},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        response_data = {}
        if purpose == PURPOSE_SIGNUP:
            user = User.objects.filter(email__iexact=email).first()
            if user and not user.is_active:
                user.is_active = True
                user.save(update_fields=["is_active"])
                logger.info(
                    f"User {user.email} verified successfully. User ID: {user.id}"
                )
        else:
            response_data["step"] = "password"

        return Response(
            {
                "success": True,
                "status": status.HTTP_200_OK,
                "message": "OTP verified successfully.",
                "data": response_data,
            },
            status=status.HTTP_200_OK,
        )


class ForgotPasswordRequestOtpView(APIView):
    """
    Generates and emails an OTP for password reset.

    Always returns the same response whether or not the email is registered,
    so the endpoint cannot be used to enumerate accounts.
    """

    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "otp"

    def post(self, request, *args, **kwargs):
        serializer = ForgotPasswordRequestOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        user = User.objects.filter(email__iexact=email).first()
        if user:
            otp_code = OtpService.generate(email, PURPOSE_PASSWORD_RESET)
            if ForgotPasswordEmailSender(user, otp_code).send_email():
                logger.info(f"Forgot password OTP sent to: {user.email}")
            else:
                logger.error("Forgot password email failed for %s", user.email)

        return Response(
            {
                "success": True,
                "status": status.HTTP_200_OK,
                "message": "If an account with that email exists, an OTP has been sent.",
                "data": {"step": "otp"},
            },
            status=status.HTTP_200_OK,
        )


class ResetPasswordView(APIView):
    """
    Verifies the password-reset OTP and sets the new password.
    """

    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "otp_verify"

    def post(self, request, *args, **kwargs):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        otp_code = serializer.validated_data["otp"]
        new_password = serializer.validated_data["new_password"]

        user = User.objects.filter(email__iexact=email).first()
        if not user or not OtpService.verify(
            email, PURPOSE_PASSWORD_RESET, otp_code, consume=True
        ):
            return Response(
                {
                    "success": False,
                    "status": status.HTTP_400_BAD_REQUEST,
                    "message": "Invalid or expired OTP.",
                    "data": {},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save(update_fields=["password"])
        clear_login_lockout(email)

        logger.info(f"Password reset successfully for: {user.email}")

        return Response(
            {
                "success": True,
                "status": status.HTTP_200_OK,
                "message": "Password has been set successfully.",
                "data": {},
            },
            status=status.HTTP_200_OK,
        )


class Country_State_List(
    generics.GenericAPIView, mixins.ListModelMixin, mixins.RetrieveModelMixin
):
    """
    Lists countries (with their states), or retrieves one country by ID.
    """

    serializer_class = CountryStateSerializer
    queryset = Country.objects.prefetch_related("states").all()
    pagination_class = None
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        if kwargs.get("pk"):
            response = self.retrieve(request, *args, **kwargs)
        else:
            response = self.list(request, *args, **kwargs)
        return Response(
            {
                "success": True,
                "status": response.status_code,
                "message": "Country fetched successfully",
                "data": response.data,
            },
            status=response.status_code,
        )


class State_List(
    generics.GenericAPIView, mixins.ListModelMixin, mixins.RetrieveModelMixin
):
    """
    Lists states (optionally filtered by ?country_id=), or retrieves one
    state by ID.
    """

    serializer_class = StateSerializer
    pagination_class = None
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        country_id = self.request.GET.get("country_id")
        if country_id:
            return State.objects.filter(country=country_id)
        return State.objects.all()

    def get(self, request, *args, **kwargs):
        if kwargs.get("pk"):
            response = self.retrieve(request, *args, **kwargs)
        else:
            response = self.list(request, *args, **kwargs)
        return Response(
            {
                "success": True,
                "status": response.status_code,
                "message": "State fetched successfully",
                "data": response.data,
            },
            status=response.status_code,
        )


class ProfileViewSet(generics.RetrieveUpdateAPIView):
    """
    API endpoint for viewing and editing the authenticated user's profile.
    """

    queryset = User.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        return Response(
            {
                "success": True,
                "status": status.HTTP_200_OK,
                "message": "Profile updated successfully",
                "data": response.data,
            },
            status=status.HTTP_200_OK,
        )

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        return Response(
            {
                "success": True,
                "status": status.HTTP_200_OK,
                "message": "Profile fetched successfully",
                "data": response.data,
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request):
        """Delete the authenticated user's profile picture."""
        user = request.user
        if not user.profile_pic:
            return Response(
                {
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "message": "No profile picture found to delete.",
                    "data": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            user.profile_pic.delete(save=False)
            user.profile_pic = None
            user.save(update_fields=["profile_pic"])
            return Response(
                {
                    "success": True,
                    "status": status.HTTP_200_OK,
                    "message": "Profile picture deleted successfully.",
                    "data": {},
                },
                status=status.HTTP_200_OK,
            )
        except Exception:
            logger.exception("Error deleting profile picture for user %s", user.pk)
            return Response(
                {
                    "success": False,
                    "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "message": "Something went wrong.",
                    "data": {},
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AddressViewSet(BaseModelViewSet):
    """
    Manages CRUD operations for user addresses.
    """

    queryset = Address.objects.all().order_by("-created_at")
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None


class ChangePasswordApiView(APIView):
    """
    Changes the authenticated user's password after verifying the old one.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        old_password = serializer.validated_data["old_password"]
        new_password = serializer.validated_data["new_password"]

        user = request.user
        if not user.check_password(old_password):
            return Response(
                {
                    "success": False,
                    "status": status.HTTP_400_BAD_REQUEST,
                    "message": "Invalid old password.",
                    "data": {},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save(update_fields=["password"])

        return Response(
            {
                "success": True,
                "status": status.HTTP_200_OK,
                "message": "Password changed successfully.",
                "data": {},
            },
            status=status.HTTP_200_OK,
        )


class AddUserApiView(APIView):
    """
    Allows admins to create a user and send them an invite email.
    """

    permission_classes = [
        permissions.IsAuthenticated,
        require_roles(ROLE_SUPER_ADMIN, ROLE_ADMIN),
    ]
    serializer_class = AdminAddUserSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        user_data = UserSerializer(user, context={"request": request}).data

        return Response(
            {
                "success": True,
                "status": status.HTTP_201_CREATED,
                "message": "User created successfully. Invite Email sent to user.",
                "data": user_data,
            },
            status=status.HTTP_201_CREATED,
        )
