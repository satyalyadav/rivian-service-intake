"""Server-side model settings with a safe representation."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from urllib.parse import urlsplit


DEFAULT_BASE_URL = "https://opencode.ai/inference/go/openai/v1"
DEFAULT_MODEL = "glm-5.3-flash"
DEFAULT_PROCESS_REQUEST_LIMIT = 24


@dataclass(frozen=True, slots=True)
class Settings:
    _api_key: str = field(repr=False)
    _base_url: str = field(repr=False)
    model: str
    process_request_limit: int
    configuration_error: str | None = None

    @property
    def configured(self) -> bool:
        return bool(self._api_key.strip())

    def __repr__(self) -> str:
        return (
            "Settings("
            f"configured={self.configured!r}, "
            f"model={self.model!r}, "
            f"process_request_limit={self.process_request_limit!r})"
        )


def _bounded_int(value: str | None, default: int, *, minimum: int, maximum: int) -> int:
    try:
        number = int(value) if value is not None else default
    except (TypeError, ValueError):
        return default
    return min(max(number, minimum), maximum)


def _validated_base_url(value: str | None) -> str:
    if value is None:
        return DEFAULT_BASE_URL
    base_url = value.strip().rstrip("/")
    try:
        parts = urlsplit(base_url)
        port = parts.port
    except ValueError:
        raise ValueError from None
    local_http = parts.hostname in {"localhost", "127.0.0.1", "::1"}
    if (
        not parts.hostname
        or any(character.isspace() for character in base_url)
        or parts.username is not None
        or parts.password is not None
        or parts.query
        or parts.fragment
        or (port is not None and not 1 <= port <= 65535)
        or (parts.scheme != "https" and not (parts.scheme == "http" and local_http))
        or len(base_url) > 300
    ):
        raise ValueError
    return base_url


def get_settings() -> Settings:
    """Read configuration from the process environment without exposing secrets."""
    model = (os.getenv("INTAKE_MODEL") or DEFAULT_MODEL).strip()
    if not model or len(model) > 100:
        model = DEFAULT_MODEL
    configuration_error = None
    try:
        base_url = _validated_base_url(os.getenv("INTAKE_BASE_URL"))
    except ValueError:
        base_url = ""
        configuration_error = (
            "INTAKE_BASE_URL must be a valid HTTPS URL. HTTP is allowed only for localhost."
        )

    return Settings(
        _api_key=os.getenv("INTAKE_API_KEY", ""),
        _base_url=base_url,
        model=model,
        process_request_limit=_bounded_int(
            os.getenv("INTAKE_PROCESS_REQUEST_LIMIT"),
            DEFAULT_PROCESS_REQUEST_LIMIT,
            minimum=1,
            maximum=500,
        ),
        configuration_error=configuration_error,
    )
