import logging

from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from .constants import ROLE_USER
from .models import User, Address, Country, State
from .utils import InviteEmailSender

logger = logging.getLogger(__name__)


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "name"]


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ["id", "name", "code"]


class StateSerializer(serializers.ModelSerializer):
    class Meta:
        model = State
        fields = ["id", "name", "country"]


class CountryStateSerializer(serializers.ModelSerializer):
    states = StateSerializer(many=True, read_only=True)

    class Meta:
        model = Country
        fields = [
            "id",
            "name",
            "code",
            "states",
        ]


class AddressSerializer(serializers.ModelSerializer):
    country = serializers.PrimaryKeyRelatedField(queryset=Country.objects.all())
    state = serializers.PrimaryKeyRelatedField(queryset=State.objects.all())

    class Meta:
        model = Address
        fields = [
            "id",
            "address_1",
            "address_2",
            "city",
            "pincode",
            "address_type",
            "country",
            "state",
        ]


class ProfilePicMixin:
    """Builds an absolute URL for the user's profile picture."""

    def get_profile_pic(self, obj):
        if not obj.profile_pic:
            return None
        url = obj.profile_pic.url
        request = self.context.get("request")
        return request.build_absolute_uri(url) if request else url


class ProfileSerializer(ProfilePicMixin, ModelSerializer):
    current_password = serializers.CharField(write_only=True, required=False)
    role = RoleSerializer(read_only=True)
    profile_pic = serializers.SerializerMethodField()
    _profile_pic_file = serializers.FileField(
        source="profile_pic", write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "username",
            "email",
            "mobile_code",
            "mobile_no",
            "gender",
            "profile_pic",
            "_profile_pic_file",
            "password",
            "current_password",
            "last_login",
            "role",
            "is_active",
        ]
        extra_kwargs = {
            "password": {"write_only": True, "required": False},
            "username": {"read_only": True},
        }

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        current_password = validated_data.pop("current_password", None)

        if password:
            if not current_password:
                raise serializers.ValidationError(
                    {"password": ["Current password is required."]}
                )
            if not instance.check_password(current_password):
                raise serializers.ValidationError(
                    {"password": ["Current password is incorrect."]}
                )
            if current_password == password:
                raise serializers.ValidationError(
                    {
                        "password": [
                            "New password should be different from the current password."
                        ]
                    }
                )
            validate_password(password, user=instance)

        if "profile_pic" in validated_data:
            self.delete_old_profile_pic(instance)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()
        return instance

    def delete_old_profile_pic(self, instance):
        """
        Deletes the old profile picture from storage when a new one is uploaded.
        """
        if instance.profile_pic:
            try:
                instance.profile_pic.delete(save=False)
            except Exception:
                logger.exception(
                    "Error deleting old profile picture for user %s", instance.pk
                )


class UserSerializer(ProfilePicMixin, ModelSerializer):
    role = RoleSerializer(read_only=True)
    profile_pic = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "username",
            "email",
            "mobile_code",
            "mobile_no",
            "gender",
            "profile_pic",
            "password",
            "is_active",
            "last_login",
            "role",
        ]
        extra_kwargs = {
            "password": {"write_only": True, "required": True},
            "username": {"read_only": True},
            "first_name": {"required": True},
            "last_name": {"required": True},
            "email": {"required": True},
        }

    def validate_email(self, value):
        return value.lower()

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.is_active = False
        user.save()

        role = Group.objects.filter(name=ROLE_USER).first()
        if role:
            user.groups.set([role])

        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True)


class VerifyOtpSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    otp = serializers.CharField(required=True)
    type = serializers.ChoiceField(
        choices=["signup", "forgot-password", "invite-accept"],
        required=False,
        allow_blank=True,
        allow_null=True,
    )


class ForgotPasswordRequestOtpSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    otp = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value


class AdminAddUserSerializer(serializers.ModelSerializer):
    role = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(), required=False, allow_null=True
    )
    is_active = serializers.BooleanField(required=False, default=True)

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "gender",
            "role",
            "is_active",
        ]
        extra_kwargs = {
            "first_name": {"required": True},
            "last_name": {"required": True},
            "email": {"required": True},
        }

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def to_representation(self, instance):
        """Return role as {id, name} object."""
        data = super().to_representation(instance)
        data["role"] = RoleSerializer(instance.role).data if instance.role else None
        return data

    def create(self, validated_data):
        role = validated_data.pop("role", None)
        if not role:
            role = Group.objects.filter(name=ROLE_USER).first()

        user = User.objects.create_user(
            email=validated_data["email"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            gender=validated_data.get("gender"),
            is_active=validated_data.get("is_active", True),
            password=None,
        )
        if role:
            user.groups.set([role])

        # Send Invite Email
        if not InviteEmailSender(user).send_email():
            logger.error("Failed to send invite email to %s", user.email)
        logger.info(f"Admin invited user: {user.email}")

        return user
