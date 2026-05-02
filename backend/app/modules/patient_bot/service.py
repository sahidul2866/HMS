from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.models.encounter import Appointment
from app.models.patient_bot import (
    GeminiAPILog,
    PatientBotAuditLog,
    PatientBotConversation,
    PatientBotFAQ,
    PatientBotIntakeAnswer,
    PatientBotIntent,
    PatientBotMessage,
    PatientBotRecommendation,
    PatientBotSetting,
    SymptomDepartmentRule,
)
from app.models.user import User
from app.modules.patient_portal.service import PatientPortalService
from app.modules.users.repository import UsersRepository
from app.schemas.patient_bot import (
    PatientBotBookAppointmentRequest,
    PatientBotConversationRead,
    PatientBotDoctorCard,
    PatientBotMessageCreate,
    PatientBotMessageRead,
    PatientBotResponse,
    PatientBotSettingsRead,
)


SYSTEM_PROMPT = (
    "You are a safe patient health assistant inside a hospital management system. Your role is to provide general "
    "educational guidance, help patients understand symptoms in simple language, suggest suitable hospital departments "
    "or doctor types, and help patients prepare for appointments. You must not diagnose disease, prescribe medicine, "
    "provide dosage, replace a doctor, or provide emergency treatment instructions. If symptoms may be serious, urgent, "
    "or worsening, advise the patient to contact emergency services or visit the nearest emergency department. Use simple, "
    "warm, respectful language. Ask for missing important context before answering. Keep responses concise and practical."
)

EMERGENCY_KEYWORDS = {
    "chest pain",
    "chest discomfort",
    "breathing difficulty",
    "shortness of breath",
    "unconscious",
    "severe bleeding",
    "stroke",
    "seizure",
    "suicidal",
    "fainting",
    "severe weakness",
    "reduced movement",
    "pregnancy bleeding",
}

INTAKE_FIELDS = ["age", "gender", "main_symptom", "duration", "severity", "existing_conditions", "current_medications"]

LOCAL_RULES = [
    {
        "keywords": ["fever", "cough", "cold", "body ache", "sore throat"],
        "department": "Medicine",
        "doctor_type": "Medicine / Internal Medicine doctor",
        "reason": "Fever, cough, body ache and sore throat are commonly first assessed by Medicine/Internal Medicine.",
    },
    {
        "keywords": ["child", "baby", "infant", "pediatric", "paediatric"],
        "department": "Pediatrics",
        "doctor_type": "Pediatrician",
        "reason": "Child health concerns are best routed to Pediatrics.",
    },
    {
        "keywords": ["stomach", "abdomen", "acidity", "vomiting", "diarrhea", "gastric"],
        "department": "Gastroenterology",
        "doctor_type": "Gastroenterologist or Medicine doctor",
        "reason": "Stomach pain, vomiting, diarrhea and acidity can need gastroenterology or medicine review.",
    },
    {
        "keywords": ["pregnant", "pregnancy", "bleeding", "period", "women", "gyne", "gynae"],
        "department": "Gynecology",
        "doctor_type": "Gynecology / Obstetrics doctor",
        "reason": "Pregnancy and women’s health concerns should be routed to Gynecology/Obstetrics.",
    },
    {
        "keywords": ["skin", "rash", "allergy", "acne", "itching"],
        "department": "Dermatology",
        "doctor_type": "Dermatologist",
        "reason": "Skin rash, allergy, acne and itching are dermatology concerns.",
    },
    {"keywords": ["tooth", "dental", "gum"], "department": "Dental", "doctor_type": "Dentist", "reason": "Tooth and gum concerns are handled by Dental."},
    {"keywords": ["eye", "vision"], "department": "Ophthalmology", "doctor_type": "Eye specialist", "reason": "Eye and vision concerns are handled by Ophthalmology."},
    {"keywords": ["ear", "nose", "throat", "ent"], "department": "ENT", "doctor_type": "ENT specialist", "reason": "Ear, nose and throat symptoms are routed to ENT."},
    {"keywords": ["bone", "joint", "injury", "fracture"], "department": "Orthopedics", "doctor_type": "Orthopedic doctor", "reason": "Bone, joint and injury symptoms are routed to Orthopedics."},
    {"keywords": ["stress", "anxiety", "sleep", "mental"], "department": "Psychiatry", "doctor_type": "Psychiatry / counseling service", "reason": "Stress, sleep and anxiety concerns can be discussed with Psychiatry or counseling."},
    {"keywords": ["chest", "heart", "palpitation"], "department": "Cardiology", "doctor_type": "Cardiologist", "reason": "Chest or heart concerns may need Cardiology; urgent symptoms should go to Emergency."},
    {"keywords": ["urine", "urinary", "kidney"], "department": "Urology", "doctor_type": "Urologist or Medicine doctor", "reason": "Urinary symptoms can need Urology or Medicine review."},
    {"keywords": ["diabetes", "thyroid", "hormone"], "department": "Endocrinology", "doctor_type": "Endocrinologist or Medicine doctor", "reason": "Diabetes, thyroid and hormone concerns are handled by Endocrinology or Medicine."},
]


class PatientBotService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.settings = get_settings()
        self.users = UsersRepository(db)

    def handle_message(self, payload: PatientBotMessageCreate, actor: User) -> PatientBotResponse:
        patient_id = self._require_patient_account(actor)
        conversation = self._get_or_create_conversation(payload.conversation_id, actor)
        message = payload.message.strip()
        self._save_message(conversation, patient_id, "patient", message, {"selected_report_id": str(payload.selected_report_id) if payload.selected_report_id else None})

        intent = self._detect_intent(message, conversation.current_intent)
        conversation.current_intent = intent
        conversation.intake = self._merge_intake(conversation.intake or {}, message, intent)
        self._save_intent(conversation, patient_id, intent)

        response = self._respond(conversation, actor, message, intent)
        self._save_message(conversation, patient_id, "bot", response.message, response.model_dump(mode="json"), response.gemini_used)
        conversation.state = "waiting_input" if response.needs_more_input else "responded"
        conversation.recommended_department = response.recommended_department
        conversation.recommended_doctor_type = response.recommended_doctor_type
        conversation.safety_level = response.safety_level
        conversation.updated_by = actor.id
        self.db.commit()
        return response

    def list_conversations(self, actor: User) -> list[PatientBotConversationRead]:
        patient_id = self._require_patient_account(actor)
        stmt = (
            select(PatientBotConversation)
            .where(PatientBotConversation.patient_id == patient_id)
            .order_by(PatientBotConversation.updated_at.desc())
        )
        return [self._conversation_read(item, include_messages=False) for item in self.db.scalars(stmt)]

    def get_conversation(self, conversation_id: UUID, actor: User) -> PatientBotConversationRead:
        patient_id = self._require_patient_account(actor)
        conversation = self.db.scalar(
            select(PatientBotConversation)
            .options(selectinload(PatientBotConversation.messages))
            .where(PatientBotConversation.id == conversation_id, PatientBotConversation.patient_id == patient_id)
        )
        if not conversation:
            raise AppException(404, "conversation_not_found", "Conversation not found")
        return self._conversation_read(conversation, include_messages=True)

    def reset(self, actor: User) -> PatientBotResponse:
        conversation = self._create_conversation(actor)
        self.db.commit()
        return PatientBotResponse(
            conversation_id=conversation.id,
            message=self.bot_settings().greeting_message,
            type="greeting",
            quick_replies=self.bot_settings().quick_replies,
            needs_more_input=False,
            next_action="choose_intent",
        )

    def suggested_doctors(self, department: str | None, actor: User) -> list[PatientBotDoctorCard]:
        return self._doctor_cards(department, actor)

    def book_appointment(self, payload: PatientBotBookAppointmentRequest, actor: User):
        patient_id = self._require_patient_account(actor)
        doctor = self.users.get_user(payload.doctor_user_id)
        if not doctor or not any(role.is_doctor_role for role in doctor.roles):
            raise AppException(404, "doctor_not_found", "Doctor not found")
        appointment = Appointment(
            branch_id=actor.branch_id or doctor.branch_id,
            patient_id=patient_id,
            doctor_user_id=doctor.id,
            appointment_number=f"APT-BOT-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
            appointment_at=payload.appointment_at,
            status="scheduled",
            reason=payload.reason,
            note="Booked from Patient Health Assistant",
            booked_by_user_id=actor.id if actor.__class__.__name__ == "User" else None,
            booked_by_patient_account_id=actor.id if actor.__class__.__name__ == "PatientPortalAccount" else None,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.db.add(appointment)
        self._audit(actor, "bot_appointment_request", {"conversation_id": str(payload.conversation_id), "doctor_id": str(doctor.id)})
        self.db.commit()
        return PatientPortalService(self.db).list_appointments(actor)[0]

    def bot_settings(self) -> PatientBotSettingsRead:
        return PatientBotSettingsRead(
            gemini_enabled=bool(self.settings.gemini_api_key),
            model_name=self.settings.gemini_model,
            max_gemini_calls_per_patient_per_day=self.settings.patient_bot_max_gemini_calls_per_day,
            greeting_message="Hi, I can help you find the right doctor, understand symptoms generally, prepare for a visit, or check hospital services. What do you need help with today?",
            quick_replies=[
                "I have symptoms",
                "I need to find a doctor",
                "I want diet guidance",
                "I want to book appointment",
                "I want to understand a report",
                "I need hospital information",
            ],
        )

    def _respond(self, conversation: PatientBotConversation, actor: User, message: str, intent: str) -> PatientBotResponse:
        lower = message.lower()
        if self._has_emergency_signal(lower):
            return self._emergency_response(conversation)
        if intent in {"greeting", "hospital_navigation", "billing_help"}:
            return self._local_info_response(conversation, intent)
        if intent in {"appointment_booking", "doctor_recommendation"} and not any(word in lower for word in ["symptom", "pain", "fever", "cough", "eat", "diet"]):
            department = self._infer_department_from_text(lower)
            doctors = self._doctor_cards(department, actor)
            return PatientBotResponse(
                conversation_id=conversation.id,
                message=f"Here are suitable doctors{f' for {department}' if department else ''}. You can choose one and request an appointment.",
                type="doctor_cards",
                recommended_department=department,
                doctor_cards=doctors,
                quick_replies=["Book appointment", "Change department", "Start over"],
                next_action="show_doctors",
            )

        missing = self._missing_intake_fields(conversation.intake or {}, intent)
        if missing:
            return PatientBotResponse(
                conversation_id=conversation.id,
                message=self._question_for_missing(missing[:2], conversation.intake or {}),
                type="intake",
                needs_more_input=True,
                quick_replies=self._quick_replies_for_field(missing[0]),
                context_summary=conversation.intake or {},
                next_action="collect_intake",
            )

        local = self._local_recommendation(conversation.intake or {}, message)
        if local and intent != "diet_guidance" and not self._needs_gemini(message):
            doctors = self._doctor_cards(local["department"], actor)
            self._save_recommendation(conversation, actor.patient_id, intent, local, doctors)
            return PatientBotResponse(
                conversation_id=conversation.id,
                message=(
                    f"Based on what you shared, {local['doctor_type']} may be suitable. {local['reason']} "
                    "If symptoms become severe, persistent, or unclear, please see a licensed doctor promptly."
                ),
                type="recommendation",
                recommended_department=local["department"],
                recommended_doctor_type=local["doctor_type"],
                safety_level=local.get("safety_level", "normal"),
                quick_replies=["Show available doctors", "Book appointment", "Ask about diet", "Start over"],
                doctor_cards=doctors,
                context_summary=conversation.intake or {},
                next_action="show_doctors",
            )

        gemini_text, gemini_used = self._gemini_or_fallback(conversation, actor, intent, local)
        doctors = self._doctor_cards(local["department"] if local else None, actor)
        return PatientBotResponse(
            conversation_id=conversation.id,
            message=gemini_text,
            type="ai_guidance" if gemini_used else "recommendation",
            recommended_department=local["department"] if local else None,
            recommended_doctor_type=local["doctor_type"] if local else None,
            safety_level=local.get("safety_level", "normal") if local else "normal",
            gemini_used=gemini_used,
            quick_replies=["Show available doctors", "Book appointment", "Start over"],
            doctor_cards=doctors,
            context_summary=conversation.intake or {},
            next_action="show_doctors" if doctors else "book_or_follow_up",
        )

    def _detect_intent(self, message: str, current: str | None = None) -> str:
        lower = message.lower()
        if any(word in lower for word in ["hi", "hello", "start over"]) and len(lower.split()) <= 3:
            return "greeting"
        if any(word in lower for word in ["diet", "eat", "food", "drink", "nutrition"]):
            return "diet_guidance"
        if any(word in lower for word in ["report", "lab", "radiology", "test result"]):
            return "report_explanation"
        if any(word in lower for word in ["prescription", "medicine instruction"]):
            return "prescription_explanation"
        if any(word in lower for word in ["book", "appointment", "slot"]):
            return "appointment_booking"
        if any(word in lower for word in ["doctor", "specialist", "gynecologist", "pediatrician", "dentist"]):
            return "doctor_recommendation"
        if any(word in lower for word in ["bill", "invoice", "payment", "receipt"]):
            return "billing_help"
        if any(word in lower for word in ["service", "location", "hour", "hospital"]):
            return "hospital_navigation"
        if any(word in lower for word in ["pain", "fever", "cough", "vomit", "rash", "chest", "stomach", "urine", "stress"]):
            return "symptom_check"
        return current or "unknown"

    def _merge_intake(self, intake: dict, message: str, intent: str) -> dict:
        lower = message.lower()
        updated = dict(intake)
        if intent in {"symptom_check", "diet_guidance", "doctor_recommendation", "report_explanation", "prescription_explanation", "unknown"}:
            if "main_symptom" not in updated and any(word in lower for word in ["fever", "cough", "pain", "rash", "stress", "diabetes", "pregnancy", "stomach", "chest"]):
                updated["main_symptom"] = message[:180]
            for severity in ["mild", "moderate", "severe"]:
                if severity in lower:
                    updated["severity"] = severity
            if any(token in lower for token in ["day", "days", "week", "weeks", "month", "months", "hour", "hours"]):
                updated.setdefault("duration", message[:80])
            if "child" in lower or "baby" in lower:
                updated["age"] = "child"
            for gender in ["male", "female"]:
                if gender in lower:
                    updated["gender"] = gender
            if any(word in lower for word in ["diabetes", "pressure", "asthma", "heart disease", "kidney"]):
                updated.setdefault("existing_conditions", message[:180])
            if any(word in lower for word in ["medicine", "medication", "tablet", "taking"]):
                updated.setdefault("current_medications", message[:180])
            if any(word in lower for word in ["pregnant", "pregnancy"]):
                updated["pregnancy_status"] = message[:120]
        return updated

    def _missing_intake_fields(self, intake: dict, intent: str) -> list[str]:
        if intent in {"greeting", "hospital_navigation", "billing_help", "appointment_booking"}:
            return []
        required = ["main_symptom", "duration", "severity"]
        if intent in {"diet_guidance", "report_explanation", "prescription_explanation"}:
            required = ["age", "main_symptom", "duration"]
        return [field for field in required if not intake.get(field)]

    def _question_for_missing(self, fields: list[str], intake: dict) -> str:
        labels = {
            "age": "Is the patient an adult or child? If you can, share the age.",
            "gender": "What is the patient's gender?",
            "main_symptom": "What is the main symptom or concern?",
            "duration": "How long has this been happening?",
            "severity": "Is it mild, moderate, or severe?",
            "existing_conditions": "Any existing condition such as diabetes, asthma, pregnancy, heart or kidney disease?",
            "current_medications": "Is the patient currently taking any regular medicine?",
        }
        return " ".join(labels[field] for field in fields if field in labels)

    def _quick_replies_for_field(self, field: str) -> list[str]:
        if field == "severity":
            return ["Mild", "Moderate", "Severe"]
        if field == "age":
            return ["Adult", "Child", "Elderly"]
        return ["Not sure", "Skip for now", "Start over"]

    def _local_recommendation(self, intake: dict, message: str) -> dict | None:
        text = f"{message} {intake.get('main_symptom', '')}".lower()
        if self._has_emergency_signal(text):
            return {"department": "Emergency", "doctor_type": "Emergency department", "reason": "Some symptoms can be urgent.", "safety_level": "urgent"}
        for rule in LOCAL_RULES:
            if any(keyword in text for keyword in rule["keywords"]):
                return {**rule, "safety_level": "normal"}
        db_rules = list(self.db.scalars(select(SymptomDepartmentRule).where(SymptomDepartmentRule.is_active.is_(True)).order_by(SymptomDepartmentRule.priority.asc())))
        for rule in db_rules:
            if any(str(keyword).lower() in text for keyword in (rule.symptom_keywords or [])):
                return {"department": rule.department, "doctor_type": rule.doctor_type, "reason": rule.reason, "safety_level": rule.safety_level}
        return None

    def _infer_department_from_text(self, lower: str) -> str | None:
        recommendation = self._local_recommendation({"main_symptom": lower}, lower)
        return recommendation["department"] if recommendation else None

    def _doctor_cards(self, department: str | None, actor: User) -> list[PatientBotDoctorCard]:
        doctors = self.users.list_doctors()
        if department:
            dep = department.lower()
            filtered = [
                doctor for doctor in doctors
                if dep in (doctor.opd_prescription_header_workplace or "").lower()
                or dep in (doctor.opd_prescription_header_specialty or "").lower()
                or dep in doctor.full_name.lower()
            ]
            doctors = filtered or doctors
        return [
            PatientBotDoctorCard(
                id=doctor.id,
                name=doctor.full_name,
                department=doctor.opd_prescription_header_workplace or "General OPD",
                specialty=doctor.opd_prescription_header_specialty or "General Consultation",
                qualification=doctor.opd_prescription_header_degrees,
                fee=str(doctor.opd_consultation_fee or "0.00"),
                chamber=doctor.opd_prescription_header_chamber,
                available_today=True,
            )
            for doctor in doctors[:6]
        ]

    def _needs_gemini(self, message: str) -> bool:
        lower = message.lower()
        return any(word in lower for word in ["why", "explain", "what could", "diet", "eat", "understand", "meaning", "mixed"])

    def _gemini_or_fallback(self, conversation: PatientBotConversation, actor: User, intent: str, local: dict | None) -> tuple[str, bool]:
        if not self.settings.gemini_api_key:
            return self._fallback_text(local, intent), False
        if self._gemini_calls_today(actor.patient_id) >= self.settings.patient_bot_max_gemini_calls_per_day:
            return self._fallback_text(local, intent), False
        context = {
            "patient_age": conversation.intake.get("age", "Not mentioned"),
            "patient_gender": conversation.intake.get("gender", "Not mentioned"),
            "main_symptom": conversation.intake.get("main_symptom", "Not mentioned"),
            "duration": conversation.intake.get("duration", "Not mentioned"),
            "severity": conversation.intake.get("severity", "Not mentioned"),
            "existing_conditions": conversation.intake.get("existing_conditions", "None mentioned"),
            "current_medications": conversation.intake.get("current_medications", "None mentioned"),
            "pregnancy_status": conversation.intake.get("pregnancy_status", "Not mentioned"),
            "patient_goal": intent,
            "available_departments": [card.department for card in self._doctor_cards(None, actor)][:8],
            "available_doctors_summary": [card.model_dump(mode="json") for card in self._doctor_cards(local["department"] if local else None, actor)[:4]],
            "safety_instruction": "Give general educational guidance only. Do not diagnose or prescribe medicine. Recommend department/doctor type and when to seek urgent care.",
        }
        try:
            text = self._call_gemini(context)
            self._log_gemini(actor, conversation, context, text, "success", None)
            return text, True
        except Exception as exc:  # noqa: BLE001
            self._log_gemini(actor, conversation, context, None, "failed", str(exc))
            return self._fallback_text(local, intent), False

    def _call_gemini(self, context: dict) -> str:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.settings.gemini_model}:generateContent?key={self.settings.gemini_api_key}"
        body = {
            "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"parts": [{"text": json.dumps(context, ensure_ascii=False)}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 420},
        }
        request = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=12) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(exc.read().decode("utf-8")[:500]) from exc
        candidates = payload.get("candidates") or []
        parts = (((candidates[0] or {}).get("content") or {}).get("parts") or []) if candidates else []
        text = " ".join(part.get("text", "") for part in parts).strip()
        if not text:
            raise RuntimeError("Gemini returned no text")
        return text

    def _fallback_text(self, local: dict | None, intent: str) -> str:
        if intent == "diet_guidance":
            return (
                "For general diet support, prefer light balanced meals, enough fluid, and easy-to-digest food. "
                "Avoid very oily or heavy food temporarily. If the patient is a child, pregnant, diabetic, elderly, "
                "or symptoms are persistent or severe, please consult a doctor or dietitian."
            )
        if local:
            return f"{local['doctor_type']} may be suitable. {local['reason']} This is general guidance, not a diagnosis."
        return "I can still help you find the right department or doctor. For detailed medical guidance, please consult a doctor."

    def _has_emergency_signal(self, lower: str) -> bool:
        return any(keyword in lower for keyword in EMERGENCY_KEYWORDS) and any(word in lower for word in ["severe", "difficulty", "sweating", "dizziness", "bleeding", "unconscious", "worse", "reduced"])

    def _emergency_response(self, conversation: PatientBotConversation) -> PatientBotResponse:
        return PatientBotResponse(
            conversation_id=conversation.id,
            message="Based on what you shared, it may be safer to seek urgent medical care now. Please contact emergency services or visit the nearest emergency department.",
            type="safety",
            safety_level="urgent",
            recommended_department="Emergency",
            recommended_doctor_type="Emergency department",
            quick_replies=["Find emergency services", "Start over"],
            next_action="emergency",
        )

    def _local_info_response(self, conversation: PatientBotConversation, intent: str) -> PatientBotResponse:
        if intent == "billing_help":
            message = "You can view invoices, receipts, paid amount and due amount from Billing. For correction or copy requests, use the Request Center."
        elif intent == "hospital_navigation":
            message = "The portal can help with OPD appointments, reports, prescriptions, billing, IPD information, documents, and health packages."
        else:
            message = self.bot_settings().greeting_message
        return PatientBotResponse(conversation_id=conversation.id, message=message, type="info", quick_replies=self.bot_settings().quick_replies, next_action="choose_intent")

    def _gemini_calls_today(self, patient_id) -> int:
        today = datetime.now(UTC) - timedelta(days=1)
        stmt = select(func.count(GeminiAPILog.id)).where(GeminiAPILog.patient_id == patient_id, GeminiAPILog.created_at >= today, GeminiAPILog.status == "success")
        return int(self.db.scalar(stmt) or 0)

    def _get_or_create_conversation(self, conversation_id: UUID | None, actor: User) -> PatientBotConversation:
        if conversation_id:
            conversation = self.db.scalar(select(PatientBotConversation).where(PatientBotConversation.id == conversation_id, PatientBotConversation.patient_id == actor.patient_id))
            if conversation:
                return conversation
        return self._create_conversation(actor)

    def _create_conversation(self, actor: User) -> PatientBotConversation:
        conversation = PatientBotConversation(
            branch_id=actor.branch_id,
            patient_id=actor.patient_id,
            user_id=actor.id if actor.__class__.__name__ == "User" else None,
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.db.add(conversation)
        self.db.flush()
        return conversation

    def _save_message(self, conversation: PatientBotConversation, patient_id, sender: str, content: str, payload: dict | None = None, gemini_used: bool = False) -> None:
        self.db.add(PatientBotMessage(conversation_id=conversation.id, patient_id=patient_id, sender=sender, content=content, payload=payload or {}, gemini_used=gemini_used))

    def _save_intent(self, conversation: PatientBotConversation, patient_id, intent: str) -> None:
        self.db.add(PatientBotIntent(conversation_id=conversation.id, patient_id=patient_id, intent=intent, confidence=80, source="local"))

    def _save_recommendation(self, conversation: PatientBotConversation, patient_id, intent: str, local: dict, doctors: list[PatientBotDoctorCard]) -> None:
        self.db.add(PatientBotRecommendation(conversation_id=conversation.id, patient_id=patient_id, intent=intent, department=local["department"], doctor_type=local["doctor_type"], reason=local["reason"], safety_level=local.get("safety_level", "normal"), payload={"doctors": [doctor.model_dump(mode="json") for doctor in doctors]}))
        for key, value in (conversation.intake or {}).items():
            self.db.add(PatientBotIntakeAnswer(conversation_id=conversation.id, patient_id=patient_id, field_name=key, answer=str(value)))

    def _log_gemini(self, actor: User, conversation: PatientBotConversation, context: dict, response: str | None, status: str, error: str | None) -> None:
        self.db.add(GeminiAPILog(branch_id=actor.branch_id, patient_id=actor.patient_id, conversation_id=conversation.id, model_name=self.settings.gemini_model, prompt_context=context, response_summary=response, status=status, error_message=error, called_at=datetime.now(UTC)))

    def _audit(self, actor: User, action: str, payload: dict) -> None:
        self.db.add(PatientBotAuditLog(branch_id=actor.branch_id, patient_id=actor.patient_id, action=action, payload=payload))

    def _conversation_read(self, conversation: PatientBotConversation, include_messages: bool) -> PatientBotConversationRead:
        messages = sorted(conversation.messages, key=lambda item: item.created_at) if include_messages else []
        return PatientBotConversationRead(
            id=conversation.id,
            title=conversation.title,
            current_intent=conversation.current_intent,
            state=conversation.state,
            intake=conversation.intake or {},
            recommended_department=conversation.recommended_department,
            recommended_doctor_type=conversation.recommended_doctor_type,
            safety_level=conversation.safety_level,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            messages=[PatientBotMessageRead.model_validate(message, from_attributes=True) for message in messages],
        )

    def _require_patient_account(self, actor: User):
        if not actor.patient_id:
            raise AppException(403, "patient_account_required", "This account is not linked to a patient")
        return actor.patient_id
