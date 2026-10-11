"""Explicit origins only; configuration is evaluated when the app is constructed."""
import json
import os
from urllib.parse import urlsplit


def allowed_origins():
    message = 'CULTIVATION_CORS_ORIGINS must be a JSON array of explicit HTTP(S) origins without paths or wildcards'
    try:
        values = json.loads(os.getenv('CULTIVATION_CORS_ORIGINS', '[]'))
        if not isinstance(values, list):
            raise ValueError(message)
        origins = []
        for value in values:
            if not isinstance(value, str):
                raise ValueError(message)
            value = value.strip()
            parts = urlsplit(value)
            if (not value or any(c.isspace() or c in '*\\' for c in value)
                or parts.scheme not in ('http', 'https') or not parts.hostname
                or parts.username is not None or parts.password is not None
                or parts.path or parts.query or parts.fragment):
                raise ValueError(message)
            parts.port  # Validate numeric port and its range.
            if value not in origins:
                origins.append(value)
        return origins
    except (ValueError, TypeError) as exc:
        raise ValueError(message) from exc
