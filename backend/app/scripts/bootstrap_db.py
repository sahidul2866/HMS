from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

from app.core.config import BASE_DIR, get_settings
from app.scripts import seed_access_control, seed_billing_catalog, seed_sample_staff

BOOTSTRAP_LOCK_ID = 91324051


def run_migrations() -> None:
    alembic_ini = Path(BASE_DIR) / "alembic.ini"
    config = Config(str(alembic_ini))
    config.set_main_option("script_location", str(Path(BASE_DIR) / "alembic"))
    config.set_main_option("sqlalchemy.url", get_settings().database_url)
    command.upgrade(config, "head")


def bootstrap_database(seed_sample_data: bool | None = None) -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
    with engine.connect() as conn:
        conn.execute(text("select pg_advisory_lock(:lock_id)"), {"lock_id": BOOTSTRAP_LOCK_ID})
        try:
            run_migrations()
            seed_access_control.main()
            seed_billing_catalog.main()
            if seed_sample_data if seed_sample_data is not None else settings.auto_seed_sample_data:
                seed_sample_staff.main()
        finally:
            conn.execute(text("select pg_advisory_unlock(:lock_id)"), {"lock_id": BOOTSTRAP_LOCK_ID})
            conn.commit()


if __name__ == "__main__":
    bootstrap_database()
