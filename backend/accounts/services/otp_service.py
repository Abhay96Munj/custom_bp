import hashlib
import hmac
import secrets

from django.core.cache import cache

# OTP purposes — a code generated for one purpose can never be used for another.
PURPOSE_SIGNUP = "signup"
PURPOSE_PASSWORD_RESET = "password-reset"


class OtpService:
    """
    Cache-backed, single-use, purpose-scoped email OTP service.

    A random 6-digit code is generated per (email, purpose) pair and stored
    hashed in the cache with a short TTL. Verification is constant-time,
    attempt-limited, and (by default) consumes the code so it cannot be
    replayed.
    """

    TTL = 600  # seconds an OTP stays valid (10 minutes)
    MAX_ATTEMPTS = 5  # wrong guesses before the OTP is invalidated

    @staticmethod
    def _key(email: str, purpose: str) -> str:
        return f"otp:{purpose}:{email.strip().lower()}"

    @staticmethod
    def _hash(otp: str) -> str:
        return hashlib.sha256(otp.encode("utf-8")).hexdigest()

    @classmethod
    def generate(cls, email: str, purpose: str) -> str:
        """Generate and store a new OTP, replacing any previous one."""
        otp = f"{secrets.randbelow(1_000_000):06d}"
        cache.set(
            cls._key(email, purpose),
            {"hash": cls._hash(otp), "attempts": 0},
            cls.TTL,
        )
        return otp

    @classmethod
    def verify(cls, email: str, purpose: str, otp: str, consume: bool = True) -> bool:
        """
        Verify a submitted OTP.

        With consume=True (default) a successful verification deletes the
        code. Use consume=False for a pre-check (e.g. a "verify OTP" step
        before the password-reset submit, which re-sends the same code).
        """
        key = cls._key(email, purpose)
        entry = cache.get(key)
        if not entry:
            return False

        if entry["attempts"] >= cls.MAX_ATTEMPTS:
            cache.delete(key)
            return False

        if not hmac.compare_digest(entry["hash"], cls._hash(otp)):
            entry["attempts"] += 1
            cache.set(key, entry, cls.TTL)
            return False

        if consume:
            cache.delete(key)
        return True
