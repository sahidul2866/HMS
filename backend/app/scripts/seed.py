from app.scripts.seed_access_control import main as seed_access_control
from app.scripts.seed_billing_catalog import main as seed_billing_catalog
from app.scripts.seed_demo_workflows import main as seed_demo_workflows
from app.scripts.seed_pharmacy_production_demo import main as seed_pharmacy_production_demo
from app.scripts.seed_sample_staff import main as seed_sample_staff


def seed() -> None:
    seed_access_control()
    seed_billing_catalog()
    seed_sample_staff()
    seed_demo_workflows()
    seed_pharmacy_production_demo()


if __name__ == "__main__":
    seed()
