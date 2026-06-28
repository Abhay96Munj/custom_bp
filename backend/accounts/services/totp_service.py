import hmac
import hashlib
import base64
import pyotp
from django.conf import settings


class TOTPService:
    """
    Stateless TOTP service for email-based OTP verification.

    The TOTP secret is derived deterministically from the user's email and
    Django SECRET_KEY using HMAC-SHA256. This means no secret ever needs to
    be stored in the database or cache — the same secret can be re-derived
    at verification time from the same inputs.
    """

    INTERVAL = 300  # 5 minutes — OTP valid window

    @staticmethod
    def _get_secret(email: str) -> str:
        """
        Derive a repeatable, cryptographically secure TOTP secret from
        email + Django SECRET_KEY.

        Uses HMAC-SHA256 so the secret is bound to this app's secret key.
        Output is base32-encoded as required by pyotp.
        """
        key = settings.SECRET_KEY.encode("utf-8")
        msg = email.strip().lower().encode("utf-8")
        digest = hmac.new(key, msg, hashlib.sha256).digest()
        return base64.b32encode(digest).decode("utf-8")

    @classmethod
    def generate_otp(cls, email: str) -> str:
        """Generate the current 6-digit OTP for the given email."""
        return pyotp.TOTP(cls._get_secret(email), interval=cls.INTERVAL).now()

    @classmethod
    def verify_otp(cls, email: str, otp: str) -> bool:
        """
        Verify a submitted OTP for the given email.

        valid_window=1 accepts the current and one adjacent window,
        allowing up to ~10 min of tolerance for clock skew or send delay.
        """
        return pyotp.TOTP(cls._get_secret(email), interval=cls.INTERVAL).verify(
            otp, valid_window=1
        )