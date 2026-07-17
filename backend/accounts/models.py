import os
import secrets

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.text import get_valid_filename, slugify

from core.models import BaseModel
from .constants import GENDER


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
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
    # Auto-generated on first save (see _generate_username); login stays
    # email-based via USERNAME_FIELD.
    username = models.CharField(max_length=150, unique=True, blank=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    email = models.EmailField(unique=True)
    mobile_code = models.CharField(max_length=30, blank=True, null=True)
    mobile_no = models.CharField(max_length=30, blank=True, null=True)
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

    def __str__(self):
        return self.email

    def _generate_username(self):
        """
        Build a unique username slug from the user's name, falling back to
        the email local part, with a random suffix on collision.
        e.g. "john-doe", "john-doe-4821".
        """
        base = slugify(f"{self.first_name} {self.last_name}".strip())
        if not base and self.email:
            base = slugify(self.email.split("@")[0])
        base = base or "user"

        candidate = base
        cls = type(self)
        while cls.objects.filter(username__iexact=candidate).exclude(pk=self.pk).exists():
            candidate = f"{base}-{secrets.randbelow(10_000):04d}"
        return candidate

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self._generate_username()
        super().save(*args, **kwargs)

    @property
    def role(self):
        """
        Returns the user's single assigned Group.
        Access pattern: user.role.name, user.role.id
        """
        return self.groups.first()

    @property
    def role_id(self):
        """
        Returns the PK of the user's group, or None.
        """
        group = self.groups.first()
        return group.pk if group else None


class Address(BaseModel):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="addresses", null=True, blank=True
    )
    country = models.ForeignKey(
        Country, on_delete=models.CASCADE, null=True, related_name="addresses"
    )
    state = models.ForeignKey(
        State, on_delete=models.CASCADE, null=True, related_name="addresses"
    )
    address_1 = models.CharField(blank=True, null=True, max_length=255)
    address_2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=50, blank=True, null=True)
    pincode = models.CharField(max_length=10, blank=True, null=True)
    address_type = models.CharField(max_length=50, default="user")
