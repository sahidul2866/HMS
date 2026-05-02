from __future__ import annotations

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.branch import Branch
from app.models.configuration import ConfigurationProfile


DEFAULT_PROFILES = [
    {
        "profile_type": "doctor_share",
        "code": "standard-opd-share",
        "name": "Standard OPD Doctor Share",
        "description": "70% doctor share, 30% hospital service share for general OPD consultation.",
        "scope": "hospital",
        "payload": {
            "method": "percentage",
            "doctor_share_percentage": 70,
            "hospital_share_percentage": 30,
            "follow_up_share_percentage": 50,
            "corporate_share_percentage": 60,
            "preview_fee": 1000,
        },
        "is_default": True,
    },
    {
        "profile_type": "prescription_suggestion",
        "code": "fever-template",
        "name": "Fever OPD Template",
        "description": "Common fever complaint, advice, medicine, investigation, and follow-up suggestions.",
        "scope": "hospital",
        "payload": {
            "complaints": ["Fever for 3 days", "Body ache", "Headache"],
            "diagnoses": ["Acute febrile illness"],
            "medicines": ["Paracetamol 500 mg - 1+1+1 after meal for 3 days", "ORS - as needed"],
            "investigations": ["CBC", "Dengue NS1", "Malaria parasite"],
            "advice": ["Take rest", "Drink adequate fluid", "Return if breathing difficulty or persistent fever"],
            "follow_up_days": 3,
        },
        "is_default": True,
    },
    {
        "profile_type": "prescription_layout",
        "code": "compact-a5-opd",
        "name": "Compact A5 OPD Prescription",
        "description": "Compact branded A5 prescription with two-column clinical body.",
        "scope": "department",
        "payload": {
            "paper_size": "A5",
            "layout": "two_column",
            "font_size": 11,
            "show_logo": True,
            "show_barcode": True,
            "sections": ["header", "patient", "complaint", "diagnosis", "rx", "investigation", "advice", "follow_up", "signature", "footer"],
            "footer_note": "Bring previous prescription and reports on follow-up.",
        },
        "is_default": True,
    },
    {
        "profile_type": "invoice_layout",
        "code": "opd-money-receipt",
        "name": "OPD Money Receipt",
        "description": "OPD receipt with patient, service table, payment, QR, cashier and signature blocks.",
        "scope": "hospital",
        "payload": {
            "template_for": "opd",
            "paper_size": "A5",
            "show_logo": True,
            "show_doctor_share": False,
            "show_qr": True,
            "columns": ["service", "qty", "rate", "discount", "total"],
            "footer_note": "Thank you for choosing our hospital.",
        },
        "is_default": True,
    },
    {
        "profile_type": "patient_portal_settings",
        "code": "standard-patient-portal",
        "name": "Standard Patient Portal Settings",
        "description": "Patient portal access, document download, family access, billing visibility and dashboard widgets.",
        "scope": "hospital",
        "payload": {
            "enabled": True,
            "allow_appointment_booking": True,
            "allow_online_payment": False,
            "allow_profile_update": True,
            "allow_family_access": True,
            "allow_document_download": True,
            "show_billing_details": True,
            "show_ipd_running_bill": True,
            "show_doctor_notes": False,
            "show_diagnosis": True,
            "show_lab_reports_before_approval": False,
            "require_profile_update_approval": True,
            "require_family_link_approval": True,
            "theme": {"logo": "default", "banner": "My Care Dashboard", "accent_color": "#0f766e"},
            "dashboard_widgets": ["appointments", "prescriptions", "reports", "billing", "documents"],
        },
        "is_default": True,
    },
    {
        "profile_type": "patient_bot_settings",
        "code": "standard-patient-bot",
        "name": "Standard Patient Health Assistant",
        "description": "Safe local-first patient bot with Gemini used only after structured context collection.",
        "scope": "hospital",
        "payload": {
            "enabled": True,
            "gemini_enabled": True,
            "gemini_model": "gemini-2.5-flash",
            "max_gemini_calls_per_patient_per_day": 5,
            "diet_guidance_enabled": True,
            "report_explanation_enabled": True,
            "prescription_explanation_enabled": True,
            "appointment_booking_enabled": True,
            "emergency_message": "Based on what you shared, it may be safer to seek urgent medical care now. Please contact emergency services or visit the nearest emergency department.",
            "quick_replies": ["I have symptoms", "Find a doctor", "Diet guidance", "Understand report", "Book appointment"],
        },
        "is_default": True,
    },
]


def main() -> None:
    session = SessionLocal()
    try:
        branch = session.scalar(select(Branch).where(Branch.code == "HQ"))
        for payload in DEFAULT_PROFILES:
            existing = session.scalar(
                select(ConfigurationProfile).where(
                    ConfigurationProfile.branch_id == (branch.id if branch else None),
                    ConfigurationProfile.profile_type == payload["profile_type"],
                    ConfigurationProfile.code == payload["code"],
                )
            )
            if existing:
                existing.name = payload["name"]
                existing.description = payload["description"]
                existing.scope = payload["scope"]
                existing.payload = payload["payload"]
                existing.is_default = payload["is_default"]
                existing.is_active = True
                continue
            session.add(ConfigurationProfile(branch_id=branch.id if branch else None, **payload))
        session.commit()
        print("Configuration demo seed completed.")
    finally:
        session.close()


if __name__ == "__main__":
    main()
