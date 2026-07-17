import logging
import os
from datetime import datetime
from email.mime.image import MIMEImage

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

LOGO_FILENAME = "Project_Name-logo.png"


class BaseEmailSender:
    """
    Base class for transactional emails: renders an HTML template with a
    plain-text fallback, attaches the inline logo, and logs failures.

    send_email() returns True on success and False on failure — callers
    decide whether a failure is fatal for their flow.
    """

    subject = ""
    template_name = ""

    def __init__(self, user):
        self.user = user
        self.from_email = settings.DEFAULT_FROM_EMAIL

    def get_context(self):
        return {
            "user": self.user,
            "now_year": datetime.now().year,
            "from_email": self.from_email,
        }

    def get_text_content(self):
        return ""

    def send_email(self):
        try:
            html_content = render_to_string(self.template_name, self.get_context())
            email = EmailMultiAlternatives(
                subject=self.subject,
                body=self.get_text_content(),
                from_email=self.from_email,
                to=[self.user.email],
            )
            email.attach_alternative(html_content, "text/html")

            logo_path = os.path.join(settings.BASE_DIR, "assets", LOGO_FILENAME)
            if os.path.exists(logo_path):
                with open(logo_path, "rb") as logo_file:
                    logo = MIMEImage(logo_file.read(), _subtype="png")
                    logo.add_header("Content-ID", "<company_logo>")
                    email.attach(logo)
            else:
                logger.warning(
                    "Email logo not found at %s; sending without it.", logo_path
                )

            email.send()
            logger.info("Sent '%s' email to %s", self.subject, self.user.email)
            return True
        except Exception:
            logger.exception(
                "Failed to send '%s' email to %s", self.subject, self.user.email
            )
            return False


class SignupEmailSender(BaseEmailSender):
    subject = "Welcome to Project_Name - Verify Your Email"
    template_name = "accounts/signup_email.html"

    def __init__(self, user, otp):
        super().__init__(user)
        self.otp = otp

    def get_context(self):
        context = super().get_context()
        context["otp"] = self.otp
        return context

    def get_text_content(self):
        return (
            f"Hello {self.user.first_name}, your OTP for Project_Name signup is "
            f"{self.otp}. It is valid for 10 minutes."
        )


class ForgotPasswordEmailSender(BaseEmailSender):
    subject = "Project_Name - Reset Your Password"
    template_name = "accounts/forgot_password_email.html"

    def __init__(self, user, otp):
        super().__init__(user)
        self.otp = otp

    def get_context(self):
        context = super().get_context()
        context["otp"] = self.otp
        return context

    def get_text_content(self):
        return (
            f"Hello {self.user.first_name}, your OTP for Project_Name password reset "
            f"is {self.otp}. It is valid for 10 minutes."
        )


class InviteEmailSender(BaseEmailSender):
    subject = "Invitation to Join Project_Name"
    template_name = "accounts/invite_email.html"

    def get_text_content(self):
        return (
            f"Hello {self.user.first_name}, you have been invited to join "
            "Project_Name! Please request a password reset OTP using your email "
            "to set up your password and access your account."
        )
