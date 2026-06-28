from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

User = get_user_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "id",
        "email",
        "mobile_no",
        "is_staff",
        "is_active",
        "created_at",
        "updated_at",
    )
    list_filter = ("is_staff", "is_active", "created_at", "updated_at")
    search_fields = ("email", "mobile_no")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at")

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Extra Fields",
            {
                "fields": (
                    "mobile_code",
                    "mobile_no",
                    "gender",
                    "profile_pic",
                    "timezone",
                    "failed_login_attempts",
                )
            },
        ),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (
            "Extra Fields",
            {
                "fields": (
                    "mobile_code",
                    "mobile_no",
                    "gender",
                    "profile_pic",
                    "timezone",
                    "failed_login_attempts",
                )
            },
        ),
    )
