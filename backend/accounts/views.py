from core.base_classes import BaseModelViewSet
from django.contrib.auth.models import Group
from .models import State, User, Address, Country, AllowedUser
from django.utils import timezone
from django.shortcuts import redirect
from .serializers import (
    UserSerializer,
    RoleSerializer,
    CountryStateSerializer,
    ProfileSerializer,
    StateSerializer,
    AddressSerializer,
    AllowedUserSerializer,
    LoginSerializer,
    VerifyOtpSerializer,
    ForgotPasswordRequestOtpSerializer,
    ResetPasswordSerializer,
    ChangePasswordSerializer,
    AdminAddUserSerializer,
)
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from rest_framework.response import Response
from django.views.generic import TemplateView
from rest_framework import generics, mixins
from rest_framework import status, permissions
from rest_framework.generics import ListAPIView
from rest_framework.views import exception_handler
from django.contrib.auth import authenticate, logout
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.permissions import AllowAny, IsAuthenticated
from datetime import timedelta
from django.contrib.auth.hashers import make_password
import datetime
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from io import StringIO
import base64
import csv
from django.contrib.auth.hashers import check_password
# import boto3
from django.conf import settings
from .utils import SignupEmailSender, validate_password, ForgotPasswordEmailSender, InviteEmailSender
from django.core.exceptions import ValidationError
from .permissions import require_permission, require_roles
from .constants import (
    ROLE_ADMIN, ROLE_SUPER_ADMIN, ROLE_HR, ROLE_MANAGER, ROLE_WORKER,
    PERM_ROLE_MANAGE,
)
from accounts.services.totp_service import TOTPService



# from store.logs import log_user_action
import logging

logger = logging.getLogger("Project_Name")


def custom_exception_handler(exc, context):
    """this function is called when an exception is generated to define the schema of
    exception response. it takes the first error message.

    Args:
        exc (Exception): generated exception

    Returns:
        Response: custom response data
    """

    response = exception_handler(exc, context)
    if response is not None:
        if isinstance(response.data, dict):
            message = None
            error_field = None
            for field, errors in response.data.items():
                if isinstance(errors, list) and len(errors) > 0:
                    message = str(errors[0])
                    error_field = field
                    break
                elif isinstance(errors, str):
                    message = errors
                    error_field = field
                    break
            
            if not message:
                message = response.data.get("detail", "An error occurred.")
            
            response.data = {
                "success": False,
                "status": response.status_code,
                "message": str(message),
                "data": {},
            }
            if error_field:
                response.data["error_field"] = error_field
        elif isinstance(response.data, list):
            message = response.data[0] if len(response.data) > 0 else "An error occurred."
            response.data = {
                "success": False,
                "status": response.status_code,
                "message": str(message),
                "data": {},
            }
        else:
            response.data = {
                "success": False,
                "status": response.status_code,
                "message": str(response.data),
                "data": {},
            }
    return response


class CustomTokenRefreshView(TokenRefreshView):
    """
    Handles refresh Token and updates the user's last login .

    Args:
        request: The HTTP request object.

    Returns:
        Response: In response it contains the new access and refresh tokens, or an error message if an exception occurs.
    """

    def post(self, request, *args, **kwargs):
        # Call the original refresh method
        response = super().post(request, *args, **kwargs)

        # Update last_login field
        try:
            access_token = response.data.get("access")
            if access_token:
                # Decode the token to get the user
                token = AccessToken(access_token)
                user_id = token["user_id"]

                # Get the user instance and update the last_login
                user_instance = User.objects.get(id=user_id)
                user_instance.last_login = timezone.now()
                user_instance.save(update_fields=["last_login"])
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "status": status.HTTP_400_BAD_REQUEST,
                    "message": str(e),
                    "data": {},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if response.status_code == status.HTTP_200_OK:
            response.data = {
                "success": True,
                "status": status.HTTP_200_OK,
                "message": "Token refreshed successfully",
                "data": response.data,
            }

        return response


"""
Admin Login
"""
class AdminLoginView(TemplateView):
    """
    Redirects to admin web login page.
    """

    def get(self, request, *args, **kwargs):
        return redirect("accounts:web_login")


class AdminUserViewSet(BaseModelViewSet):
    """
    Manages admin user operations.
    Restricted to Super Admin and Admin roles only.
    """

    queryset = User.objects.all().order_by("-created_at")
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated, require_roles(ROLE_SUPER_ADMIN, ROLE_ADMIN)]

"""
SignUp Api
"""


class SignupApiView(APIView):
    """
    Handles user registration and OTP generation.
    """

    # permission_classes = (AllowAny,)


    def post(self, request, *args, **kwargs):
        """
        Processes user signup and sends OTP.
        """
        serializer = UserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate TOTP-based OTP and send verification email
        otp_code = TOTPService.generate_otp(user.email)
        SignupEmailSender(user, otp_code).send_email()

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
    This LoginApiView class handles user login.

    Only Admin users can log in. The API validates credentials,
    checks account status, and returns tokens upon successful login.
    Methods:
        post(request): Handles admin login.
    """

    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        
        user_agent = request.headers.get("User-Agent")
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]

        # # Check if email is in AllowedUser list
        # if not AllowedUser.objects.filter(email=email).exists():
        #     return Response(
        #         {
        #             "message": "The site is currently undergoing updates. Please try again later.",
        #             "status": False,
        #         },
        #         status=status.HTTP_403_FORBIDDEN,
        #     )
       
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "status": status.HTTP_400_BAD_REQUEST,
                    "message": "We couldn't find an account with that email. Please sign up.",
                    "data": {},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Authenticate
        user_auth = authenticate(username=email, password=password)
        if not user_auth:
            user.failed_login_attempts += 1
            user.save(update_fields=["failed_login_attempts"])
            remaining = 4 - user.failed_login_attempts
            
            if remaining <= 0:
                return Response(
                    {
                        "success": False,
                        "status": status.HTTP_429_TOO_MANY_REQUESTS,
                        "message": "Too many login attempts. Please use 'Forgot Password' to reset your password.",
                        "data": {},
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

            return Response(
                {
                    "success": False,
                    "status": status.HTTP_400_BAD_REQUEST,
                    "message": f"Invalid credentials. {remaining} attempts left.",
                    "data": {},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Reset failed attempts on successful login
        user.failed_login_attempts = 0
        user.last_login = timezone.now()
        user.save(update_fields=["failed_login_attempts", "last_login"])

       
        if not user.is_active:
            return Response(
                {
                    "success": False,
                    "status": status.HTTP_400_BAD_REQUEST,
                    "message": "Your account has been deactivated. Please contact admin to activate your account.",
                    "data": {},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        logger.info(f"User {user.email} logged in successfully. User ID: {user.id}")

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        data = UserSerializer(user, context={"request": request}).data
        data.update(
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
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
    This LogOutView class handles user logout.

    Allows authenticated users to log out by invalidating their refresh token,
    clearing the session, and updating the last login timestamp.

    Methods:
        post(request): Handles user logout.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            user = request.user
            logger.info(
                f"User {user.email} logged out successfully. User ID: {user.id}"
            )
            user.last_login = timezone.now()
            user.save(update_fields=["last_login"])
            refresh_token = request.data.get("refresh_token")
            token = RefreshToken(refresh_token)
            token.blacklist()
            logout(request)
            request.session.flush()

            return Response(
                {
                    "success": True,
                    "status": status.HTTP_205_RESET_CONTENT,
                    "message": "Logged out Successfully",
                    "data": {},
                },
                status=status.HTTP_205_RESET_CONTENT,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "status": status.HTTP_400_BAD_REQUEST,
                    "message": "Bad request",
                    "data": {"error": str(e)},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class TestingResponse(APIView):
    """
    Tests authentication for users. Returns test response for authenticated users.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        print("request.user", request.user.role)
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
    permission_classes = [permissions.IsAuthenticated, require_permission(PERM_ROLE_MANAGE)]


class VerifyOtpView(APIView):
    """
    This VerifyOtpView class handles OTP verification.

    Users can verify their OTP for login or registration. The API validates the
    provided email and OTP, checks for expiry, and activates the user account
    upon successful verification.

    Methods:
        post(request): Handles OTP verification.
    """

    permission_classes = (permissions.AllowAny,)

    def post(self, request, *args, **kwargs):
        serializer = VerifyOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_email = serializer.validated_data["email"]
        otp_sent = serializer.validated_data["otp"]
        req_type = serializer.validated_data.get("type")

        user = User.objects.filter(email=user_email).first()
        if not user:
            return Response(
                {
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "message": "Invalid User email provided! Please provide a correct email.",
                    "data": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Verify OTP using stateless TOTP
        if not TOTPService.verify_otp(user_email, otp_sent):
            return Response(
                {
                    "success": False,
                    "status": status.HTTP_400_BAD_REQUEST,
                    "message": "Invalid or expired OTP.",
                    "data": {},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.is_active = True
        user.save()

        logger.info(f"User {user.email} OTP verified successfully. User ID: {user.id}")

        response_data = {}
        if req_type in ["forgot-password", "invite-accept"]:
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
    Handle POST request to generate and send OTP for password reset.

    This method generates a one-time password (OTP) for a user who has forgotten
    their password. It creates or updates an OTP entry in the database and sends
    the OTP to the user's email.

    Parameters:
    - request (HttpRequest): The HTTP request object.
    - *args: Variable length argument list.
    - **kwargs: Arbitrary keyword arguments.

    Returns:
    - Response: A Django Rest Framework Response object containing:
        - status (bool): Indicates whether the operation was successful.
        - message (str): A descriptive message about the result of the operation.
        - HTTP status code:
            - 200 OK if OTP was successfully sent
            - 400 BAD REQUEST if email is not provided
            - 404 NOT FOUND if user with provided email does not exist
    """

    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = ForgotPasswordRequestOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        user = User.objects.filter(email=email).first()
        if not user:
            return Response(
                {
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "message": "User with this email does not exist.",
                    "data": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Generate TOTP-based OTP — no secret stored anywhere
        otp_code = TOTPService.generate_otp(email)
        ForgotPasswordEmailSender(user, otp_code).send_email()
        logger.info(f"Forgot password OTP sent to: {user.email}")

        return Response(
            {
                "success": True,
                "status": status.HTTP_200_OK,
                "message": "OTP has been sent to your email.",
                "data": {"step": "otp"},

            },
            status=status.HTTP_200_OK,
        )


class ResetPasswordView(APIView):
    """
    Verifies OTP and resets user password.
    """

    permission_classes = [permissions.AllowAny]
    def post(self, request, *args, **kwargs):
        logger.info("ResetPasswordView called with data: %s", request.data)
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        otp_code = serializer.validated_data["otp"]
        new_password = serializer.validated_data["new_password"]

        # Fetch user by email
        user = User.objects.filter(email=email).first()
        if not user:
            return Response(
                {
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "message": "User with this email does not exist.",
                    "data": {},
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Verify OTP — stateless TOTP, no DB lookup needed
        if not TOTPService.verify_otp(email, otp_code):
            return Response(
                {
                    "success": False,
                    "status": status.HTTP_400_BAD_REQUEST,
                    "message": "Invalid or expired OTP.",
                    "data": {},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # OTP valid — reset password and clear failed login attempts
        user.password = make_password(new_password)
        user.failed_login_attempts = 0
        user.save(update_fields=["password", "failed_login_attempts"])

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
    A view for retrieving a list of countries and their associated states.

    This view provides functionality to either list all countries and their states
    or retrieve a specific country by its ID. It uses the CountryStateSerializer
    for data serialization and doesn't apply pagination to the results.

    Attributes:
        serializer_class (Serializer): The serializer class for country and state data.
        queryset (QuerySet): The base queryset for retrieving countries, including related states.
        pagination_class (None): Pagination is disabled for this view.
    """

    serializer_class = CountryStateSerializer
    queryset = Country.objects.prefetch_related("states").all()
    pagination_class = None
    permission_classes = [permissions.AllowAny]

    @swagger_auto_schema(
        operation_description="Get a list of countries and their states, or retrieve a specific country by its ID.",
        responses={
            200: openapi.Response(
                description="Country and state list retrieved successfully",
                schema=CountryStateSerializer(many=True),
            ),
            400: openapi.Response(
                description="Bad request, invalid input parameters or failed retrieval"
            ),
        },
    )
    def get(self, request, *args, **kwargs):
        if kwargs.get("pk"):
            response = self.retrieve(request, *args, **kwargs)
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
    A view for retrieving a list of states or a specific state.

    This view provides functionality to either list all states, states for a specific country,
    or retrieve a specific state by its ID. It uses the StateSerializer for data serialization
    and doesn't apply pagination to the results.

    Attributes:
        serializer_class (Serializer): The serializer class for state data.
        pagination_class (None): Pagination is disabled for this view.
    """

    serializer_class = StateSerializer
    pagination_class = None

    def get_queryset(self):
        """
        Get the list of items for this view.

        If a country_id is provided in the request's GET parameters, it returns
        states filtered by that country. Otherwise, it returns all states.

        Returns:
            QuerySet: A queryset of State objects, filtered by country if specified.
        """
        country_id = self.request.GET.get("country_id")
        print("country_id", country_id)
        if country_id:
            return State.objects.filter(country=country_id)
        return State.objects.all()

    @swagger_auto_schema(
        operation_description="Get a list of states for a specific country, or all states if no country is provided.",
        manual_parameters=[
            openapi.Parameter(
                "country_id",
                openapi.IN_QUERY,
                description="ID of the country to filter states",
                type=openapi.TYPE_INTEGER,
            )
        ],
        responses={
            200: openapi.Response(
                description="List of states successfully retrieved",
                schema=StateSerializer(many=True),
            ),
            400: openapi.Response(description="Bad request, invalid parameters"),
        },
    )
    def get(self, request, *args, **kwargs):
        """
        Handle GET requests to retrieve state(s).

        This method either retrieves a list of all states, states for a specific country,
        or a single state if a primary key (pk) is provided in the URL.

        Args:
            request (HttpRequest): The request object.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments. May contain 'pk' for retrieving a specific state.

        Returns:
            Response: A response object with the following structure:
                {
                    "status": True,
                    "status_code": <HTTP_STATUS_CODE>,
                    "message": "State fetched successfully",
                    "data": <SERIALIZED_STATE_DATA>
                }
        """
        if kwargs.get("pk"):
            response = self.retrieve(request, *args, **kwargs)
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
    API endpoint for viewing and editing user profiles.
    """

    queryset = User.objects.all()
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """
        Retrieve the authenticated user's profile.

        Returns:
            User: The currently authenticated user object.
        """

        return self.request.user

    @swagger_auto_schema(
        operation_description="Update the authenticated user's profile.",
        responses={
            200: openapi.Response(
                description="User profile updated successfully",
                schema=ProfileSerializer,
            ),
            400: openapi.Response(description="Bad request, invalid data."),
            401: openapi.Response(
                description="Authentication credentials were not provided."
            ),
        },
    )
    def update(self, request, *args, **kwargs):
        """
        Update the authenticated user's profile.

        This method overrides the default update behavior to provide a custom response format.

        Args:
            request (HttpRequest): The HTTP request object.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: A custom response object containing the updated profile data,
                      along with status information and a success message.
        """

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

    @swagger_auto_schema(
        operation_description="Retrieve the authenticated user's profile.",
        responses={
            200: openapi.Response(
                description="User profile retrieved successfully",
                schema=ProfileSerializer,
            ),
            401: openapi.Response(
                description="Authentication credentials were not provided."
            ),
        },
    )
    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve the authenticated user's profile.

        This method overrides the default retrieve behavior to provide a custom response format.

        Args:
            request (HttpRequest): The HTTP request object.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Response: A custom response object containing the user's profile data,
                      along with status information and a success message.
        """

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

    @swagger_auto_schema(
        operation_description="Delete the authenticated user's profile picture.",
        responses={
            200: openapi.Response(description="Profile picture deleted successfully."),
            404: openapi.Response(description="No profile picture found to delete."),
            500: openapi.Response(
                description="Internal server error, something went wrong."
            ),
        },
    )
    def delete(self, request):
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
            key = user.profile_pic.name
            user.profile_pic.delete(save=False)
            user.profile_pic = None
            user.save()
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
    permission_classes = [permissions.IsAuthenticated]
    """
    API endpoint to change user password.

    Users need to provide their email, old password, and new password.
    The old password is validated before updating to the new password.

    Methods:
        post(request): Handles password change.
    """

    def post(self, request, *args, **kwargs):
        email = request.user.email
        if not email:
            return Response(
                {
                    "success": False,
                    "status": status.HTTP_400_BAD_REQUEST,
                    "message": "Please enter email",
                    "data": {},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        old_password = serializer.validated_data["old_password"]
        new_password = serializer.validated_data["new_password"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "status": status.HTTP_404_NOT_FOUND,
                    "message": "User not found.",
                    "data": {},
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not check_password(old_password, user.password):
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
        user.save()

        return Response(
            {
                "success": True,
                "status": status.HTTP_200_OK,
                "message": "Password changed successfully.",
                "data": {},
            },
            status=status.HTTP_200_OK,
        )
        
class AllowedUserViewSet(BaseModelViewSet):
    """
    Manages the allowlist of permitted user emails.
    Restricted to Super Admin and Admin roles only.
    """
    queryset = AllowedUser.objects.all()
    serializer_class = AllowedUserSerializer
    permission_classes = [permissions.IsAuthenticated, require_roles(ROLE_SUPER_ADMIN, ROLE_ADMIN)]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class AddUserApiView(APIView):
    permission_classes = [permissions.IsAuthenticated, require_roles(ROLE_SUPER_ADMIN, ROLE_ADMIN)]
    serializer_class = AdminAddUserSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data, context={"request": request})
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
    