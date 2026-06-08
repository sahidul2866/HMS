from __future__ import annotations

from app.scripts.seed_access_control import main as seed_access_control
from app.scripts.seed_accounting_demo import main as seed_accounting_demo
from app.scripts.seed_billing_catalog import main as seed_billing_catalog
from app.scripts.seed_configuration_demo import main as seed_configuration_demo
from app.scripts.seed_dashboard_timeseries import main as seed_dashboard_timeseries
from app.scripts.seed_demo_workflows import main as seed_demo_workflows
from app.scripts.seed_hr_demo import main as seed_hr_demo
from app.scripts.seed_inventory_demo import main as seed_inventory_demo
from app.scripts.seed_ot_demo import main as seed_ot_demo
from app.scripts.seed_patient_bot_demo import main as seed_patient_bot_demo
from app.scripts.seed_pharmacy_production_demo import main as seed_pharmacy_production_demo
from app.scripts.seed_sample_staff import main as seed_sample_staff


def main(include_sample_staff: bool = True) -> None:
    seed_access_control()
    seed_billing_catalog()
    if not include_sample_staff:
        return
    seed_sample_staff()
    seed_demo_workflows()
    seed_pharmacy_production_demo()
    seed_inventory_demo()
    seed_hr_demo()
    seed_ot_demo()
    seed_accounting_demo()
    seed_configuration_demo()
    seed_patient_bot_demo()
    seed_dashboard_timeseries()


if __name__ == "__main__":
    main()
