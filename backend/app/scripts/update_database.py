from app.scripts.bootstrap_db import run_migrations
from app.scripts.seed_access_control import main as seed_access_control
from app.scripts.seed_billing_catalog import main as seed_billing_catalog
from app.scripts.seed_sample_staff import main as seed_sample_staff


def main() -> None:
    run_migrations()
    seed_access_control()
    seed_billing_catalog()
    seed_sample_staff()
    print("Database updated with migrations and seed scripts.")


if __name__ == "__main__":
    main()
