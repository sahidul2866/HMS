"""Add ten clearly labelled pending invoices to test billing and referrals.

Local development only. Repeat runs preserve all existing rows, including
payments made while testing these invoices.
"""
import json

from app.core.config import get_settings
from app.core.database import engine
from app.scripts.seed_complete_demo import DEMO, Fixtures


def main():
    if get_settings().app_env != "development" or engine.url.host not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("Pending bill samples require a local development database.")
    with engine.begin() as connection:
        f = Fixtures(connection)
        patient = f.lookup("patients", patient_number="PAT-DEMO-FULL")
        cashier = f.lookup("users", username="billing_rashid", email="rashid.billing@hms.local")
        doctor = f.lookup("users", username="dr_rahman", email="dr.rahman@hms.local")
        referral_examples = {
            9: (f.lookup("users", username="surgeon_arif"), "Dr. Arif Khan"),
            10: (f.lookup("users", username="anesthetist_faria"), "Dr. Faria Islam"),
        }
        for index in range(1, 11):
            amount = index * 100
            referral_id, referral_name = referral_examples.get(index, (doctor, "Dr. Rahman"))
            key = f"pending-bills-demo-{index}"
            invoice = f.put(
                "billing_invoices", key=key, patient_id=patient,
                invoice_number=f"DEMO-PENDING-{index:02d}", status="posted",
                sub_total=amount, total_amount=amount, paid_amount=0,
                due_amount=amount, payment_status="unpaid",
                discount_percentage=0, discount_amount=0, referred_doctor_amount=0,
                internal_referral_user_id=referral_id, referred_doctor_name=referral_name,
                billed_by_user_id=cashier, source_module="billing", note=DEMO,
            )
            f.put(
                "billing_invoice_items", key=key, invoice_id=invoice,
                service_name=f"DEMO pending bill example {index}", quantity=1,
                unit_price=amount, line_total=amount,
                doctor_share_percentage=0, doctor_share_amount=0,
                source_label="DEMO queue testing only",
            )
        added = f.added
    print(json.dumps({"inserted_rows": added, "invoice_prefix": "DEMO-PENDING-", "initial_demo_due": 5500}))


if __name__ == "__main__":
    main()
