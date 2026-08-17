from __future__ import annotations

import os
import sys
from pathlib import Path

from typing import Iterable

from a2wsgi import ASGIMiddleware

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("APP_ENV", "production")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("AUTO_DB_BOOTSTRAP", "false")

from app.main import app  # noqa: E402

_adapter: ASGIMiddleware | None = None
_adapter_pid: int | None = None


def application(environ: dict, start_response: object) -> Iterable[bytes]:
    """Expose FastAPI as WSGI, initializing the event loop after worker fork."""
    global _adapter, _adapter_pid
    process_id = os.getpid()
    if _adapter is None or _adapter_pid != process_id:
        _adapter = ASGIMiddleware(app, wait_time=60)
        _adapter_pid = process_id
    return _adapter(environ, start_response)
