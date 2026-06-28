from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from .constants import GENDER
from django.utils.text import get_valid_filename
import os
from django.conf import settings
from core.models import BaseModel


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        extra_fields.setdefault("username", email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class Country(BaseModel):
    name = models.CharField(max_length=255, unique=True)
    code = models.CharField(
        max_length=5, unique=True
    )  # e.g., "IN" for India, "US" for the USA

    def __str__(self):
        return self.name


class State(BaseModel):
    name = models.CharField(max_length=255)
    country = models.ForeignKey(
        Country, on_delete=models.CASCADE, related_name="states"
    )

    class Meta:
        unique_together = (
            "name",
            "country",
        )  # A state should be unique within a country

    def __str__(self):
        return f"{self.name}, {self.country.name}"


def user_profile_pic_upload_to(instance, filename):
    user_id = instance.id
    valid_filename = get_valid_filename(filename)
    return os.path.join("profile_pic", str(user_id), valid_filename)


class User(AbstractUser):
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    username = models.CharField(max_length=254, blank=True, null=True)
    email = models.EmailField(unique=True)
    mobile_code = models.CharField(max_length=30, blank=True, null=True)
    mobile_no = models.CharField(max_length=30, blank=True, null=True)
    # age = models.IntegerField(blank=True, null=True)
    gender = models.CharField(max_length=1, choices=GENDER, null=True, blank=True)
    profile_pic = models.FileField(
        upload_to=user_profile_pic_upload_to, blank=True, null=True
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    timezone = models.CharField(max_length=50, blank=True, null=True)
    failed_login_attempts = models.PositiveIntegerField(default=0)
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UserManager()

    class Meta:
        permissions = [
            ("user_view",   "Can view users"),
            ("user_create", "Can create users"),
            ("user_edit",   "Can edit users"),
            ("user_delete", "Can delete users"),
            ("role_manage", "Can manage roles/groups"),
            ("hr_view",     "Can view HR data"),
            ("report_view", "Can view reports"),
        ]

    @property
    def role(self):
        """
        Returns the user's single assigned Group.
        Backwards-compatible replacement for the old Roles ForeignKey.
        Access pattern: user.role.name, user.role.id
        """
        return self.groups.first()

    @property
    def role_id(self):
        """
        Returns the PK of the user's group, or None.
        Backwards-compatible replacement for user.role_id.
        """
        group = self.groups.first()
        return group.pk if group else None

    def save(self, *args, **kwargs):
        self.username = self.email
        super().save(*args, **kwargs)


class Address(BaseModel):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="addresses", null=True, blank=True
    )
    country = models.ForeignKey(
        Country, on_delete=models.CASCADE, null=True, related_name="country"
    )
    state = models.ForeignKey(
        State, on_delete=models.CASCADE, null=True, related_name="state"
    )
    address_1 = models.CharField(blank=True, null=True, max_length=255)
    address_2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=50, blank=True, null=True)
    pincode = models.CharField(max_length=10, blank=True, null=True)
    address_type = models.CharField(max_length=50, default="user")
    deleted_at = models.DateTimeField(null=True, blank=True)


class AllowedUser(BaseModel):
    email = models.EmailField(unique=True)

    def __str__(self):
        return self.email