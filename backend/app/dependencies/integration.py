from fastapi import Header

from app.core.config import get_settings
from app.core.exceptions import AppException


def verify_machine_integration_key(x_machine_key: str | None = Header(default=None)) -> None:
    expected = get_settings().machine_integration_key
    if not expected or x_machine_key != expected:
        raise AppException(401, "invalid_machine_key", "Invalid machine integration key")
