"""
Dev-server settings: local settings plus CORS/CSRF origins for a frontend
served from another host/port.
"""

import os

from .local import *  # noqa

CORS_ALLOWED_ORIGINS = [
    origin
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS", "http://localhost:9080"
    ).split(",")
    if origin
]

CSRF_TRUSTED_ORIGINS = [
    origin
    for origin in os.getenv(
        "CSRF_TRUSTED_ORIGINS", "http://localhost:9080"
    ).split(",")
    if origin
]
