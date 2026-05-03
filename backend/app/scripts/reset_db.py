"""Destructive database reset + re-seed script.

Requires environment variable RESET_DB_CONFIRM=YES to run.

Usage:
    cd backend
    RESET_DB_CONFIRM=YES .venv/bin/python -m app.scripts.reset_db
"""

import logging
import os
import subprocess
import sys

from app.core.database import SessionLocal
from app.scripts.seed import seed
from app.scripts.seed_lab_radiology_demo import seed as seed_lab_radiology

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("reset_db")


def reset_db() -> None:
    if os.environ.get("RESET_DB_CONFIRM") != "YES":
        logger.error("Environment variable RESET_DB_CONFIRM=YES is required to run this script.")
        logger.error("This will DESTROY all data in the configured database.")
        sys.exit(1)

    logger.warning("=== DESTRUCTIVE DATABASE RESET STARTED ===")

    # Drop all tables via alembic downgrade or raw SQL
    from app.core.config import get_settings
    from app.core.database import engine
    from app.models.base import Base

    # Drop all tables
    logger.info("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    logger.info("All tables dropped.")

    # Run alembic upgrade head
    logger.info("Running alembic upgrade head...")
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        logger.error(f"Alembic upgrade failed: {result.stderr}")
        sys.exit(1)
    logger.info("Alembic upgrade completed.")

    # Run seed pipeline
    logger.info("Running seed pipeline...")
    seed()
    logger.info("Base seed completed.")

    logger.info("Running lab/radiology demo seed...")
    seed_lab_radiology()
    logger.info("Lab/radiology demo seed completed.")

    logger.warning("=== DATABASE RESET COMPLETED ===")


if __name__ == "__main__":
    reset_db()
