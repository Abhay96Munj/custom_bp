from django.test import TestCase
from django.contrib.auth.models import Group
from accounts.models import User
from accounts.serializers import UserSerializer, AdminAddUserSerializer
from accounts.constants import ROLE_USER, ROLE_ADMIN

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

        # Check role property and group assignment
        self.assertIsNotNone(user.role)
        self.assertEqual(user.role.name, ROLE_USER)
        self.assertEqual(user.role.pk, 2)
        
        # Check serialized output
        serialized_data = UserSerializer(user).data
        self.assertEqual(serialized_data["role"]["id"], 2)
        self.assertEqual(serialized_data["role"]["name"], ROLE_USER)

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
