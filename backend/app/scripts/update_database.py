from app.scripts.bootstrap_db import run_migrations
from app.scripts.script_checkpoints import run_checkpoint_step
from app.scripts.seed_access_control import main as seed_access_control
from app.scripts.seed_billing_catalog import main as seed_billing_catalog
from app.scripts.seed_sample_staff import main as seed_sample_staff


def main() -> None:
    run_checkpoint_step("update_database", "migrations", lambda: (run_migrations(), "Alembic upgraded to head")[1])
    run_checkpoint_step("update_database", "access_control", lambda: (seed_access_control(), "Access control seeded")[1])
    run_checkpoint_step("update_database", "billing_catalog", lambda: (seed_billing_catalog(), "Billing catalog seeded")[1])
    run_checkpoint_step("update_database", "sample_staff", lambda: (seed_sample_staff(), "Sample staff seeded")[1])
    print("Database updated with migrations and seed scripts.")


if __name__ == "__main__":
    main()
