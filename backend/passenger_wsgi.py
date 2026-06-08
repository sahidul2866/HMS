from __future__ import annotations

import os
import sys
from pathlib import Path

from a2wsgi import ASGIMiddleware

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("APP_ENV", "production")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("AUTO_DB_BOOTSTRAP", "false")

from app.main import app  # noqa: E402

application = ASGIMiddleware(app)
