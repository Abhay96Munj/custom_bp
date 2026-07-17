from django.contrib.auth.models import Group
from django.test import TestCase, override_settings

from accounts.constants import ROLE_ADMIN, ROLE_USER
from accounts.serializers import AdminAddUserSerializer, UserSerializer
from accounts.services.otp_service import (
    OtpService,
    PURPOSE_PASSWORD_RESET,
    PURPOSE_SIGNUP,
)


class UserSignupRoleTestCase(TestCase):
    def setUp(self):
        # Create groups since tests run on a clean, empty test database
        self.admin_group = Group.objects.create(pk=1, name=ROLE_ADMIN)
        self.user_group = Group.objects.create(pk=2, name=ROLE_USER)

    def test_signup_assigns_default_user_role(self):
        data = {
            "first_name": "Test",
            "last_name": "User",
            "email": "testsignup@example.com",
            "password": "Securepassword123!",
        }
        serializer = UserSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()

        # Signups start inactive until OTP verification
        self.assertFalse(user.is_active)

        # Check role property and group assignment
        self.assertIsNotNone(user.role)
        self.assertEqual(user.role.name, ROLE_USER)

        # Check serialized output
        serialized_data = UserSerializer(user).data
        self.assertEqual(serialized_data["role"]["name"], ROLE_USER)

    def test_username_is_generated_from_name(self):
        data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "password": "Securepassword123!",
        }
        serializer = UserSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()
        self.assertEqual(user.username, "john-doe")

    def test_username_collision_gets_suffix(self):
        for i in range(2):
            serializer = UserSerializer(
                data={
                    "first_name": "John",
                    "last_name": "Doe",
                    "email": f"john{i}@example.com",
                    "password": "Securepassword123!",
                }
            )
            self.assertTrue(serializer.is_valid(), serializer.errors)
            user = serializer.save()

        self.assertNotEqual(user.username, "john-doe")
        self.assertTrue(user.username.startswith("john-doe-"))

    def test_admin_add_user_assigns_specified_role(self):
        data = {
            "first_name": "Admin",
            "last_name": "Added",
            "email": "adminadded@example.com",
            "role": self.admin_group.pk,
        }
        serializer = AdminAddUserSerializer(data=data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        user = serializer.save()

        self.assertIsNotNone(user.role)
        self.assertEqual(user.role.name, ROLE_ADMIN)


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
)
class OtpServiceTestCase(TestCase):
    EMAIL = "otp@example.com"

    def test_generated_otp_verifies_once(self):
        otp = OtpService.generate(self.EMAIL, PURPOSE_SIGNUP)
        self.assertTrue(OtpService.verify(self.EMAIL, PURPOSE_SIGNUP, otp))
        # Consumed — the same OTP cannot be replayed
        self.assertFalse(OtpService.verify(self.EMAIL, PURPOSE_SIGNUP, otp))

    def test_wrong_otp_fails(self):
        otp = OtpService.generate(self.EMAIL, PURPOSE_SIGNUP)
        wrong = "000000" if otp != "000000" else "111111"
        self.assertFalse(OtpService.verify(self.EMAIL, PURPOSE_SIGNUP, wrong))
        # The right code still works after a wrong guess
        self.assertTrue(OtpService.verify(self.EMAIL, PURPOSE_SIGNUP, otp))

    def test_otp_is_purpose_scoped(self):
        otp = OtpService.generate(self.EMAIL, PURPOSE_SIGNUP)
        self.assertFalse(OtpService.verify(self.EMAIL, PURPOSE_PASSWORD_RESET, otp))

    def test_non_consuming_verify_allows_reuse(self):
        otp = OtpService.generate(self.EMAIL, PURPOSE_PASSWORD_RESET)
        self.assertTrue(
            OtpService.verify(self.EMAIL, PURPOSE_PASSWORD_RESET, otp, consume=False)
        )
        self.assertTrue(OtpService.verify(self.EMAIL, PURPOSE_PASSWORD_RESET, otp))

    def test_attempt_limit_invalidates_otp(self):
        otp = OtpService.generate(self.EMAIL, PURPOSE_SIGNUP)
        wrong = "000000" if otp != "000000" else "111111"
        for _ in range(OtpService.MAX_ATTEMPTS):
            self.assertFalse(OtpService.verify(self.EMAIL, PURPOSE_SIGNUP, wrong))
        # Too many wrong guesses — even the correct OTP is now rejected
        self.assertFalse(OtpService.verify(self.EMAIL, PURPOSE_SIGNUP, otp))
