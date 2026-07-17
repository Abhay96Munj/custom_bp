"""
Production settings. Everything sensitive or environment-specific comes from
environment variables; the process refuses to start if the essentials are
missing.

Required environment variables:
    DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS, DATABASE_URL, CELERY_BROKER_URL
"""

import os

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa

DEBUG = False

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise ImproperlyConfigured(
        "The DJANGO_SECRET_KEY environment variable is required in production."
    )

ALLOWED_HOSTS = [
    host for host in os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",") if host
]
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "The DJANGO_ALLOWED_HOSTS environment variable is required in production."
    )

if not os.getenv("DATABASE_URL"):
    raise ImproperlyConfigured(
        "The DATABASE_URL environment variable is required in production."
    )

DATABASES = {
    "default": dj_database_url.config(conn_max_age=600, conn_health_checks=True)
}
DATABASES["default"]["ATOMIC_REQUESTS"] = True

CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL")
REDIS_URL = os.getenv("CELERY_BROKER_URL")

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "True") == "True"
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", "False") == "True"
EMAIL_PORT = int(os.getenv("EMAIL_PORT") or 587)
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL")

CORS_ALLOWED_ORIGINS = [
    origin for origin in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if origin
]
CSRF_TRUSTED_ORIGINS = [
    origin for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if origin
]

# HTTPS / security hardening. SECURE_SSL_REDIRECT can be disabled when TLS
# terminates at a load balancer that already redirects HTTP.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = os.getenv("DJANGO_SECURE_SSL_REDIRECT", "True") == "True"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30  # 30 days; raise once verified
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
