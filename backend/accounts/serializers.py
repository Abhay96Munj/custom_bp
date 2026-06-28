import random
import os
import datetime
import logging
from rest_framework.serializers import ModelSerializer
from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import Group
from .models import User, Address, Country, State, AllowedUser
from django.utils import timezone
from .utils import SignupEmailSender, validate_password
from core.validation_messages import VALIDATION_ERROR_MESSAGES
from .utils import SignupEmailSender, validate_password, InviteEmailSender

logger = logging.getLogger("Project_Name")


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
    class Meta:
        model = Country
        fields = [
            "id",
            "name",
            "code",
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


class ProfileSerializer(ModelSerializer):
    current_password = serializers.CharField(write_only=True)
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
        }

    def get_profile_pic(self, obj):
        if not obj.profile_pic:
            return None
        from core.base_classes import get_asset_url
        return get_asset_url(obj.profile_pic.name, is_protected=False)

    def update(self, instance, validated_data):
        if "profile_pic" in validated_data:
            self.delete_old_profile_pic(instance)

        for attr, value in validated_data.items():
            if attr == "password":
                instance.password = make_password(value)
            else:
                setattr(instance, attr, value)

        if validated_data.get("password"):
            current_password = validated_data.get("current_password")
            if not current_password:
                raise serializers.ValidationError(
                    {"password": ["Current password is required."]}
                )
            if not instance.check_password(current_password):
                raise serializers.ValidationError(
                    {"password": ["Current password is incorrect."]}
                )
            if current_password == validated_data["password"]:
                raise serializers.ValidationError(
                    {
                        "password": [
                            "New password should be different from the current password."
                        ]
                    }
                )
            instance.password = make_password(validated_data["password"])

        instance.save()
        return instance

    def delete_old_profile_pic(self, instance):
        """
        Deletes the old profile picture if it exists and a new one is uploaded.
        """
        if instance.profile_pic:
            try:
                old_pic_path = instance.profile_pic.path
                if os.path.isfile(old_pic_path):
                    os.remove(old_pic_path)
            except Exception as e:
                print(f"Error deleting old profile picture: {e}")


class UserSerializer(ModelSerializer):
    role = RoleSerializer(read_only=True)
    profile_pic = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "first_name",
            "last_name",
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
            "password": {
                "write_only": True,
                "required": True,
                "error_messages": VALIDATION_ERROR_MESSAGES["password"]
            },
            "first_name": {
                "required": True,
                "error_messages": VALIDATION_ERROR_MESSAGES["first_name"]
            },
            "last_name": {
                "required": True,
                "error_messages": VALIDATION_ERROR_MESSAGES["last_name"]
            },
            "email": {
                "required": True,
                "error_messages": VALIDATION_ERROR_MESSAGES["email"]
            },
        }

    def get_profile_pic(self, obj):
        if not obj.profile_pic:
            return None
        from core.base_classes import get_asset_url
        return get_asset_url(obj.profile_pic.name, is_protected=False)

    def validate_password(self, password):
        return validate_password(password)

    def create(self, validated_data):
        validated_data.pop("role", None)
        validated_data["password"] = make_password(validated_data["password"])
        validated_data["is_active"] = False
        user = User.objects.create(**validated_data)

        from django.contrib.auth.models import Group
        from .constants import ROLE_USER
        role = Group.objects.filter(name=ROLE_USER).first() or Group.objects.filter(pk=2).first()
        if role:
            user.groups.set([role])

        return user



class AllowedUserSerializer(ModelSerializer):
    class Meta:
        model = AllowedUser
        fields = ["id", "email", "created_at", "created_by"]
        read_only_fields = ["id", "created_at", "created_by"]


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(
        required=True,
        error_messages=VALIDATION_ERROR_MESSAGES["email"]
    )
    password = serializers.CharField(
        required=True,
        error_messages=VALIDATION_ERROR_MESSAGES["password"]
    )


class VerifyOtpSerializer(serializers.Serializer):
    email = serializers.EmailField(
        required=True,
        error_messages={
            "required": VALIDATION_ERROR_MESSAGES["email_otp"]["email_required"],
            "blank": VALIDATION_ERROR_MESSAGES["email_otp"]["email_required"],
            "invalid": VALIDATION_ERROR_MESSAGES["email"]["invalid"],
        }
    )
    otp = serializers.CharField(
        required=True,
        error_messages={
            "required": VALIDATION_ERROR_MESSAGES["email_otp"]["otp_required"],
            "blank": VALIDATION_ERROR_MESSAGES["email_otp"]["otp_required"],
        }
    )
    type = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class ForgotPasswordRequestOtpSerializer(serializers.Serializer):
    email = serializers.EmailField(
        required=True,
        error_messages={
            "required": VALIDATION_ERROR_MESSAGES["forgot_password"]["email_required"],
            "blank": VALIDATION_ERROR_MESSAGES["forgot_password"]["email_required"],
            "invalid": VALIDATION_ERROR_MESSAGES["email"]["invalid"],
        }
    )


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(
        required=True,
        error_messages={
            "required": VALIDATION_ERROR_MESSAGES["forgot_password"]["email_required"],
            "blank": VALIDATION_ERROR_MESSAGES["forgot_password"]["email_required"],
            "invalid": VALIDATION_ERROR_MESSAGES["email"]["invalid"],
        }
    )
    otp = serializers.CharField(
        required=True,
        error_messages={
            "required": VALIDATION_ERROR_MESSAGES["forgot_password"]["otp_required"],
            "blank": VALIDATION_ERROR_MESSAGES["forgot_password"]["otp_required"],
        }
    )
    new_password = serializers.CharField(
        required=True,
        error_messages={
            "required": VALIDATION_ERROR_MESSAGES["forgot_password"]["new_password_required"],
            "blank": VALIDATION_ERROR_MESSAGES["forgot_password"]["new_password_required"],
        }
    )

    def validate_new_password(self, value):
        from .utils import validate_password
        validate_password(value)
        return value


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(
        required=True,
        error_messages={
            "required": VALIDATION_ERROR_MESSAGES["change_password"]["old_password_required"],
            "blank": VALIDATION_ERROR_MESSAGES["change_password"]["old_password_required"],
        }
    )
    new_password = serializers.CharField(
        required=True,
        error_messages={
            "required": VALIDATION_ERROR_MESSAGES["change_password"]["new_password_required"],
            "blank": VALIDATION_ERROR_MESSAGES["change_password"]["new_password_required"],
        }
    )

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
        """Return role as {id, name} object (same API shape as before)."""
        data = super().to_representation(instance)
        data['role'] = RoleSerializer(instance.role).data if instance.role else None
        return data

    def create(self, validated_data):
        from .constants import ROLE_USER
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
        invite_email_sender = InviteEmailSender(user)
        invite_email_sender.send_email()
        logger.info(f"Admin invited user: {user.email}")

        return user
