from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_patient_account_or_superadmin_demo
from app.modules.patient_bot.service import PatientBotService
from app.schemas.patient_bot import (
    PatientBotBookAppointmentRequest,
    PatientBotConversationRead,
    PatientBotDoctorCard,
    PatientBotMessageCreate,
    PatientBotResponse,
    PatientBotSettingsRead,
)
from app.schemas.portal import PatientAppointmentRead

router = APIRouter(prefix="/patient-bot", tags=["Patient Health Assistant"])


@router.post("/message", response_model=PatientBotResponse)
def patient_bot_message(payload: PatientBotMessageCreate, user=Depends(get_current_patient_account_or_superadmin_demo), db: Session = Depends(get_db)) -> PatientBotResponse:
    return PatientBotService(db).handle_message(payload, user)


@router.get("/conversations", response_model=list[PatientBotConversationRead])
def patient_bot_conversations(user=Depends(get_current_patient_account_or_superadmin_demo), db: Session = Depends(get_db)) -> list[PatientBotConversationRead]:
    return PatientBotService(db).list_conversations(user)


@router.get("/conversations/{conversation_id}", response_model=PatientBotConversationRead)
def patient_bot_conversation(conversation_id: UUID, user=Depends(get_current_patient_account_or_superadmin_demo), db: Session = Depends(get_db)) -> PatientBotConversationRead:
    return PatientBotService(db).get_conversation(conversation_id, user)


@router.post("/reset", response_model=PatientBotResponse)
def patient_bot_reset(user=Depends(get_current_patient_account_or_superadmin_demo), db: Session = Depends(get_db)) -> PatientBotResponse:
    return PatientBotService(db).reset(user)


@router.get("/suggested-doctors", response_model=list[PatientBotDoctorCard])
def patient_bot_suggested_doctors(
    department: str | None = Query(default=None),
    user=Depends(get_current_patient_account_or_superadmin_demo),
    db: Session = Depends(get_db),
) -> list[PatientBotDoctorCard]:
    return PatientBotService(db).suggested_doctors(department, user)


@router.post("/book-appointment-request", response_model=PatientAppointmentRead)
def patient_bot_book_appointment(
    payload: PatientBotBookAppointmentRequest,
    user=Depends(get_current_patient_account_or_superadmin_demo),
    db: Session = Depends(get_db),
) -> PatientAppointmentRead:
    return PatientBotService(db).book_appointment(payload, user)


@router.get("/settings", response_model=PatientBotSettingsRead)
def patient_bot_settings(db: Session = Depends(get_db)) -> PatientBotSettingsRead:
    return PatientBotService(db).bot_settings()
