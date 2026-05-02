from __future__ import annotations

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.branch import Branch
from app.models.patient_bot import PatientBotFAQ, PatientBotSetting, SymptomDepartmentRule


RULES = [
    (["fever", "cough", "cold", "body ache"], "Medicine", "Medicine / Internal Medicine doctor", "Fever, cough and body ache are commonly first assessed by Medicine/Internal Medicine."),
    (["child", "baby", "infant"], "Pediatrics", "Pediatrician", "Child health concerns should be reviewed by Pediatrics."),
    (["stomach", "abdomen", "vomiting", "diarrhea", "acidity"], "Gastroenterology", "Gastroenterologist or Medicine doctor", "Digestive symptoms may need Gastroenterology or Medicine review."),
    (["pregnancy", "pregnant", "women", "period"], "Gynecology", "Gynecology / Obstetrics doctor", "Pregnancy and women’s health concerns are routed to Gynecology/Obstetrics."),
    (["chest", "heart", "palpitation"], "Cardiology", "Cardiologist", "Chest or heart concerns may need Cardiology; urgent symptoms should go to Emergency."),
    (["skin", "rash", "allergy"], "Dermatology", "Dermatologist", "Skin rash and allergy concerns are routed to Dermatology."),
    (["tooth", "dental"], "Dental", "Dentist", "Tooth and gum concerns are handled by Dental."),
    (["eye", "vision"], "Ophthalmology", "Eye specialist", "Eye and vision concerns are handled by Ophthalmology."),
    (["ear", "nose", "throat"], "ENT", "ENT specialist", "Ear, nose and throat concerns are routed to ENT."),
]

FAQS = [
    ("What should I bring to my appointment?", ["bring", "appointment", "prepare"], "Bring previous prescriptions, reports, current medicine list, patient ID, and any insurance or corporate document if applicable."),
    ("Where can I see reports?", ["report", "lab", "radiology"], "Approved lab and radiology reports are available in the portal Report and Document Center sections."),
    ("How do I get an invoice copy?", ["invoice", "receipt", "bill"], "Open Billing or Document Center to download available invoices and receipts. Use Request Center if you need a staff-issued copy."),
]


def main() -> None:
    db = SessionLocal()
    try:
        branch = db.scalar(select(Branch).where(Branch.code == "HQ"))
        for keywords, department, doctor_type, reason in RULES:
            existing = db.scalar(select(SymptomDepartmentRule).where(SymptomDepartmentRule.branch_id == (branch.id if branch else None), SymptomDepartmentRule.department == department))
            if existing:
                existing.symptom_keywords = keywords
                existing.doctor_type = doctor_type
                existing.reason = reason
                continue
            db.add(SymptomDepartmentRule(branch_id=branch.id if branch else None, symptom_keywords=keywords, department=department, doctor_type=doctor_type, reason=reason, urgent_keywords=["severe", "breathing difficulty", "bleeding", "unconscious"]))
        for question, keywords, answer in FAQS:
            existing = db.scalar(select(PatientBotFAQ).where(PatientBotFAQ.branch_id == (branch.id if branch else None), PatientBotFAQ.question == question))
            if existing:
                existing.keywords = keywords
                existing.answer = answer
                continue
            db.add(PatientBotFAQ(branch_id=branch.id if branch else None, question=question, keywords=keywords, answer=answer))
        setting = db.scalar(select(PatientBotSetting).where(PatientBotSetting.branch_id == (branch.id if branch else None), PatientBotSetting.key == "default"))
        payload = {
            "enabled": True,
            "gemini_enabled": True,
            "max_gemini_calls_per_patient_per_day": 5,
            "diet_guidance_enabled": True,
            "report_explanation_enabled": True,
            "prescription_explanation_enabled": True,
            "appointment_booking_enabled": True,
            "emergency_message": "Based on what you shared, it may be safer to seek urgent medical care now.",
            "quick_replies": ["I have symptoms", "Find a doctor", "Diet guidance", "Understand report", "Book appointment"],
        }
        if setting:
            setting.value = payload
        else:
            db.add(PatientBotSetting(branch_id=branch.id if branch else None, key="default", value=payload))
        db.commit()
        print("Patient bot demo seed completed.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
