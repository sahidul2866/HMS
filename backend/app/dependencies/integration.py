import hmac

from fastapi import Header

from app.core.config import get_settings
from app.core.exceptions import AppException

# Value shipped in source control; anyone can read it, so it must never authorise machines in production.
SHIPPED_DEFAULT_KEY = "hms-machine-key"


def verify_machine_integration_key(x_machine_key: str | None = Header(default=None)) -> None:
    settings = get_settings()
    expected = settings.machine_integration_key
    if settings.app_env == "production" and expected == SHIPPED_DEFAULT_KEY:
        raise AppException(503, "machine_key_not_configured", "Set MACHINE_INTEGRATION_KEY before accepting machine uploads")
    if not expected or not x_machine_key or not hmac.compare_digest(x_machine_key.encode(), expected.encode()):
        raise AppException(401, "invalid_machine_key", "Invalid machine integration key")
