from app.scripts.bootstrap_db import run_migrations
from app.scripts.seed_access_control import main as seed_access_control
from app.scripts.seed_billing_catalog import main as seed_billing_catalog
from app.scripts.seed_demo_workflows import main as seed_demo_workflows
from app.scripts.seed_pharmacy_production_demo import main as seed_pharmacy_production_demo
from app.scripts.seed_sample_staff import main as seed_sample_staff


def main(include_sample_staff: bool = True) -> None:
    run_migrations()
    seed_access_control()
    seed_billing_catalog()
    if include_sample_staff:
        seed_sample_staff()
        seed_demo_workflows()
        seed_pharmacy_production_demo()
    print("Database updated with migrations and seed scripts.")


if __name__ == "__main__":
    main()
