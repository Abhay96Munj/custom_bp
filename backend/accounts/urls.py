from .views import (
    SignupApiView,
    LoginApiView,
    LogOutView,
    TestingResponse,
    RoleView,
    CustomTokenRefreshView,
    VerifyOtpView,
    ForgotPasswordRequestOtpView,
    ResetPasswordView,
    ProfileViewSet,
    Country_State_List,
    State_List,
    AddressViewSet,
    ChangePasswordApiView,
    AllowedUserViewSet,
    AddUserApiView
)

# from .web_views import *
from django.urls import path
from django.contrib import admin
from rest_framework_simplejwt.views import (
    TokenVerifyView,
)
from rest_framework import routers
from .views import AdminUserViewSet

admin.autodiscover()


app_name = "accounts"

router = routers.DefaultRouter()
router.register(r"address", AddressViewSet)
router.register(r"admin-users", AdminUserViewSet, basename="admin-user")
router.register(r"allowed-users", AllowedUserViewSet, basename="allowed-users")


urlpatterns = [
    ## Authentication
    path("signup/", SignupApiView.as_view(), name="signup_api"),
    path("login/", LoginApiView.as_view(), name="login_api"),
    path("logout/", LogOutView.as_view(), name="logout_api"),
    path("profile/", ProfileViewSet.as_view(), name="profile_api"),
    path("refresh/", CustomTokenRefreshView.as_view(), name="token_refresh"),
    path("check/", TestingResponse.as_view(), name="testing"),
    path("verify/", TokenVerifyView.as_view(), name="verify"),
    path("role/", RoleView.as_view(), name="RoleView"),
    path("change_password/", ChangePasswordApiView.as_view(), name="change-password"),
    path("verify-otp/", VerifyOtpView.as_view(), name="verify-otp"),
    path("add-user/", AddUserApiView.as_view(), name="add-user"),
    path("request-otp/", ForgotPasswordRequestOtpView.as_view(), name="request-otp"),
    path(
        "reset-password/",
        ResetPasswordView.as_view(),
        name="reset-password",
    ),
    path("country-list/", Country_State_List.as_view(), name="country-state-list"),
    path(
        "country-list/<int:pk>/",
        Country_State_List.as_view(),
        name="country-state-list",
    ),
    path("state-list/", State_List.as_view(), name="country-state-list"),
    path(
        "state-list/<int:pk>/",
        State_List.as_view(),
        name="country-state-list",
    ),
]


urlpatterns += router.urls
