#!/usr/bin/env python3
"""ayrshare_api_retriever.py

Verify Ayrshare API credentials without publishing any posts.

Environment variables:
    AYRSHARE_API_KEY        (required)
    AYRSHARE_PROFILE_KEY    (optional)
    AYRSHARE_API_BASE_URL   (optional, default: https://api.ayrshare.com/api)
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError

DEFAULT_BASE_URL = "https://api.ayrshare.com/api"
USER_AGENT = "shopify-meta-commerce-ops/ayrshare-key-check"
REQUEST_TIMEOUT_SECONDS = 20
MAX_BODY_BYTES = 1_000_000  # cap how much of a response we read
MAX_DETAIL_CHARS = 500      # cap diagnostic text length
TEST_PAYLOAD = {
    "post": "Credential validation check. This content must not be published."
}


class ConfigurationError(Exception):
    """Raised when required configuration is missing."""


class AyrshareValidationError(Exception):
    """Raised when credential validation fails. Message is sanitized."""


@dataclass(frozen=True)
class AyrshareCredentials:
    api_key: str
    profile_key: Optional[str] = None

    def __repr__(self) -> str:
        # Prevent accidental credential exposure via repr/print/logging.
        return "AyrshareCredentials(api_key='***', profile_key='***' if set)"

    __str__ = __repr__


def load_credentials() -> AyrshareCredentials:
    api_key = (os.getenv("AYRSHARE_API_KEY") or "").strip()
    if not api_key:
        raise ConfigurationError(
            "AYRSHARE_API_KEY environment variable is missing or empty."
        )
    profile_key = (os.getenv("AYRSHARE_PROFILE_KEY") or "").strip() or None
    return AyrshareCredentials(api_key=api_key, profile_key=profile_key)


def get_base_url() -> str:
    base = (os.getenv("AYRSHARE_API_BASE_URL") or "").strip() or DEFAULT_BASE_URL
    return base.rstrip("/")


def build_headers(credentials: AyrshareCredentials) -> Dict[str, str]:
    headers = {
        "Authorization": f"Bearer {credentials.api_key}",
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
    }
    if credentials.profile_key:
        headers["Profile-Key"] = credentials.profile_key
    return headers


def _redact(text: str, credentials: AyrshareCredentials) -> str:
    """Remove any credential values from text and truncate it."""
    for secret in (credentials.api_key, credentials.profile_key):
        if secret:
            text = text.replace(secret, "[REDACTED]")
    if len(text) > MAX_DETAIL_CHARS:
        text = text[:MAX_DETAIL_CHARS] + "...[truncated]"
    return text


def _parse_json(raw: bytes) -> Any:
    if not raw:
        return {}
    try:
        return json.loads(raw.decode("utf-8", errors="replace"))
    except (ValueError, TypeError):
        return {"raw": "non-JSON response body"}


def validate_credentials(credentials: AyrshareCredentials) -> Dict[str, Any]:
    """POST a test payload to /validate/post. Never publishes."""
    endpoint = f"{get_base_url()}/validate/post"
    body = json.dumps(TEST_PAYLOAD).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=body,
        headers=build_headers(credentials),
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            status_code = resp.getcode()
            parsed = _parse_json(resp.read(MAX_BODY_BYTES))
    except HTTPError as exc:
        try:
            detail = exc.read(MAX_BODY_BYTES).decode("utf-8", errors="replace")
        except Exception:
            detail = ""
        detail = _redact(detail, credentials)
        raise AyrshareValidationError(
            f"HTTP {exc.code} from {endpoint}: {exc.reason}."
            + (f" Response: {detail}" if detail else "")
        ) from None
    except URLError as exc:
        reason = _redact(str(exc.reason), credentials)
        raise AyrshareValidationError(
            f"Network error contacting {endpoint}: {reason}"
        ) from None
    except TimeoutError:
        raise AyrshareValidationError(
            f"Request to {endpoint} timed out after {REQUEST_TIMEOUT_SECONDS}s."
        ) from None

    # Redact the parsed response in case the API echoes credentials back.
    safe_response = json.loads(_redact(json.dumps(parsed), credentials)) \
        if len(json.dumps(parsed)) <= MAX_DETAIL_CHARS else {
            "note": "response omitted (too large)"
        }

    return {
        "ok": 200 <= status_code < 300,
        "status_code": status_code,
        "endpoint": endpoint,
        "published": False,
        "response": safe_response,
    }


def main() -> int:
    try:
        credentials = load_credentials()
        result = validate_credentials(credentials)
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 1
    except AyrshareValidationError as exc:
        print(f"Validation error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # last-resort guard; message only, no traceback
        print(f"Unexpected error: {type(exc).__name__}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())