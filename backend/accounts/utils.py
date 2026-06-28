import os
import logging
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.contrib.sites.shortcuts import get_current_site
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.mail import send_mail
from datetime import datetime, timedelta
from random import randint
from accounts.models import User
from datetime import datetime
from django.conf import settings
from email.mime.image import MIMEImage
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
logger = logging.getLogger("Project_Name")
from django.contrib.auth import get_user_model
User = get_user_model()
from django.core.exceptions import ValidationError

class SignupEmailSender:


    def __init__(self, user, otp):
        self.user = user
        self.otp = otp
        self.subject = "Welcome to Project_Name - Verify Your Email"
        self.from_email = settings.DEFAULT_FROM_EMAIL

    def build_html_content(self):
        context = {
            'user': self.user,
            'otp': self.otp,
            'now_year': datetime.now().year,
            'from_email': self.from_email,
        }
        return render_to_string('accounts/signup_email.html', context)

    def send_email(self):
        try:
            html_content = self.build_html_content()
            text_content = f"Hello {self.user.first_name}, your OTP for Project_Name signup is {self.otp}. It is valid for 30 minutes."
            
            email = EmailMultiAlternatives(
                subject=self.subject,
                body=text_content,
                from_email=self.from_email,
                to=[self.user.email],
            )
            email.attach_alternative(html_content, "text/html")
            

            logo_path = os.path.join(settings.BASE_DIR, "assets", "Project_Name-logo.png")
            with open(logo_path, "rb") as logo_file:
                logo = MIMEImage(logo_file.read(), _subtype="png")
                logo.add_header("Content-ID", "<company_logo>")
                email.attach(logo)
            
            logger.info("Sending signup OTP email")
            email.send()
            logger.info("Signup OTP email sent successfully")
            return True

        except Exception as e:
            logger.error(f"Error sending signup OTP email to {self.user.email}: {str(e)}")
            return False




def SendUserEmail1(
    request,
    user,
    template_name,
    mail_subject,
    to_email,
    token,
    description,
    title,
    password,
):
    use_https = False
    current_site = get_current_site(request)
    site_name = current_site.name
    context = {
        "domain": current_site.domain,
        "site_name": site_name,
        "protocol": "https" if use_https else "http",
        "user": user,
        "token": token if token else "",
        "description": description if description else "",
        "title": title if title else "",
    }
    try:
        # Preparing email
        message = render_to_string(str(template_name), context)
        email_message = EmailMultiAlternatives(
            mail_subject, message, settings.EMAIL_HOST_USER, [to_email]
        )
        html_email = render_to_string(str(template_name), context)
        email_message.attach_alternative(html_email, "text/html")

        logger.info("Sending email (SendUserEmail1)")

        status = email_message.send()

        logger.info("Email sent successfully (SendUserEmail1)")

        return status

    except Exception as e:
        logger.error(
            f"Error sending email (SendUserEmail1): {str(e)}"
        )
        raise


def send_user_email(user: User):

    otp = Otp.objects.filter(user=user).first()
    logger.info("Sending email (send_user_email)")

    try:
        status = send_mail(
            "Your OTP Code",
            f"Dear {user.first_name} {user.last_name},\nYour OTP code is {otp.otp}. It will expire in 30 minutes.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )

        logger.info("Email sent successfully (send_user_email)")

        return status

    except Exception as e:
        logger.error(f" Error sending email (send_user_email): {str(e)}")
        raise       

def get_pagination(request, data):
    page = request.GET.get("page", 1)
    paginator = Paginator(data, 10)
    try:
        data = paginator.page(page)
    except PageNotAnInteger:
        data = paginator.page(1)
    except EmptyPage:
        data = paginator.page(paginator.num_pages)
    except Exception:
        data = None
    return data


def validate_password(password):
    
    if len(password) < 10:
        raise ValidationError(
            "Password must be at least 10 characters long."
        )

    if not any(c.isupper() for c in password):
        raise ValidationError(
            "Password must contain at least one uppercase letter."
        )

    if not any(c.islower() for c in password):
        raise ValidationError(
            "Password must contain at least one lowercase letter."
        )

    if not any(c.isdigit() for c in password):
        raise ValidationError(
            "Password must contain at least one digit."
        )
        
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?/"
    if not any(c in special_chars for c in password):
        raise ValidationError(
            "Password must contain at least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?/)."
        )
    
    return password

class ForgotPasswordEmailSender:

    def __init__(self, user, otp):
        self.user = user
        self.otp = otp
        self.subject = "Project_Name - Reset Your Password"
        self.from_email = settings.DEFAULT_FROM_EMAIL

    def build_html_content(self):
        context = {
            'user': self.user,
            'otp': self.otp,
            'now_year': datetime.now().year,
            'from_email': self.from_email,
        }
        return render_to_string('accounts/forgot_password_email.html', context)

    def send_email(self):
        try:
            html_content = self.build_html_content()
            text_content = f"Hello {self.user.first_name}, your OTP for Project_Name password reset is {self.otp}. It is valid for 30 minutes."
            
            email = EmailMultiAlternatives(
                subject=self.subject,
                body=text_content,
                from_email=self.from_email,
                to=[self.user.email],
            )
            email.attach_alternative(html_content, "text/html")
            
            logo_path = os.path.join(settings.BASE_DIR, "assets", "Project_Name-logo.png")
            with open(logo_path, "rb") as logo_file:
                logo = MIMEImage(logo_file.read(), _subtype="png")
                logo.add_header("Content-ID", "<company_logo>")
                email.attach(logo)
            
            logger.info("Sending forgot password OTP email")
            email.send()
            logger.info("Forgot password OTP email sent successfully")
            return True

        except Exception as e:
            logger.error(f"Error sending forgot password OTP email to {self.user.email}: {str(e)}")
            return False


class InviteEmailSender:
    def __init__(self, user):
        self.user = user
        self.subject = "Invitation to Join Project_Name"
        self.from_email = settings.DEFAULT_FROM_EMAIL

    def build_html_content(self):
        context = {
            'user': self.user,
            'now_year': datetime.now().year,
            'from_email': self.from_email,
        }
        return render_to_string('accounts/invite_email.html', context)

    def send_email(self):
        try:
            html_content = self.build_html_content()
            text_content = f"Hello {self.user.first_name}, you have been invited to join Project_Name! Please request a password reset OTP using your email to set up your password and access your account."
            
            email = EmailMultiAlternatives(
                subject=self.subject,
                body=text_content,
                from_email=self.from_email,
                to=[self.user.email],
            )
            email.attach_alternative(html_content, "text/html")
            
            logo_path = os.path.join(settings.BASE_DIR, "assets", "Project_Name-logo.png")
            if os.path.exists(logo_path):
                with open(logo_path, "rb") as logo_file:
                    logo = MIMEImage(logo_file.read(), _subtype="png")
                    logo.add_header("Content-ID", "<company_logo>")
                    email.attach(logo)
            
            logger.info("Sending invite email")
            email.send()
            logger.info("Invite email sent successfully")
            return True

        except Exception as e:
            logger.error(f"Error sending invite email to {self.user.email}: {str(e)}")
            return False
