from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_request_context
from app.dependencies.permissions import require_any_permissions, require_permissions
from app.modules.telemedicine.service import TelemedicineService
from app.schemas.telemedicine import (
    TelemedicineAppointmentCreate,
    TelemedicineAppointmentRead,
    TelemedicineChatCreate,
    TelemedicineChatRead,
    TelemedicineConsentUpdate,
    TelemedicineConsultationRead,
    TelemedicineConsultationUpdate,
    TelemedicineDashboardRead,
    TelemedicineFileCreate,
    TelemedicineFileRead,
    TelemedicineInvestigationCreate,
    TelemedicineInvestigationRead,
    TelemedicinePaymentUpdate,
    TelemedicineReportRead,
    TelemedicineSettingCreate,
    TelemedicineSettingRead,
    TelemedicineStatusUpdate,
)

router = APIRouter(prefix="/telemedicine", tags=["Telemedicine"])


def appointment_payload(item) -> dict:
    data = {column.name: getattr(item, column.name) for column in item.__table__.columns}
    data["patient_name"] = f"{item.patient.first_name} {item.patient.last_name}".strip() if item.patient else None
    data["patient_number"] = item.patient.patient_number if item.patient else None
    data["doctor_name"] = item.doctor.full_name if item.doctor else None
    data["uploaded_files"] = item.uploaded_files or []
    return data


def consultation_payload(item) -> dict:
    data = {column.name: getattr(item, column.name) for column in item.__table__.columns}
    data["telemedicine_number"] = item.telemedicine_appointment.telemedicine_number if item.telemedicine_appointment else None
    data["patient_name"] = f"{item.patient.first_name} {item.patient.last_name}".strip() if item.patient else None
    data["patient_number"] = item.patient.patient_number if item.patient else None
    data["doctor_name"] = item.doctor.full_name if item.doctor else None
    data["completed_by_name"] = item.completed_by.full_name if item.completed_by else None
    data["media_status"] = item.media_status or {}
    return data


def chat_payload(item) -> dict:
    data = {column.name: getattr(item, column.name) for column in item.__table__.columns}
    data["sender_name"] = item.sender_user.full_name if item.sender_user else f"{item.sender_patient.first_name} {item.sender_patient.last_name}".strip() if item.sender_patient else None
    return data


def file_payload(item) -> dict:
    data = {column.name: getattr(item, column.name) for column in item.__table__.columns}
    data["uploaded_by_name"] = item.uploaded_by.full_name if item.uploaded_by else None
    return data


@router.get("/dashboard", response_model=TelemedicineDashboardRead, dependencies=[Depends(require_permissions("telemedicine.view"))])
def dashboard(doctor_id: UUID | None = None, department: str | None = None, date_filter: date | None = Query(default=None, alias="date"), status: str | None = None, appointment_type: str | None = None, payment_status: str | None = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    filters = {k: v for k, v in {"doctor_id": doctor_id, "department": department, "date": date_filter, "status": status, "appointment_type": appointment_type, "payment_status": payment_status}.items() if v is not None}
    return TelemedicineService(db).dashboard(user, filters)


@router.get("/appointments", response_model=list[TelemedicineAppointmentRead], dependencies=[Depends(require_permissions("telemedicine.view"))])
def list_appointments(doctor_id: UUID | None = None, department: str | None = None, status: str | None = None, payment_status: str | None = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    filters = {k: v for k, v in locals().items() if k not in {"user", "db"} and v is not None}
    return [TelemedicineAppointmentRead.model_validate(appointment_payload(item)) for item in TelemedicineService(db).list_appointments(user, filters)]


@router.post("/appointments", response_model=TelemedicineAppointmentRead, dependencies=[Depends(require_permissions("telemedicine.appointment.create"))])
def create_appointment(payload: TelemedicineAppointmentCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    item = TelemedicineService(db).create_appointment(payload, user, context)
    db.commit()
    db.refresh(item)
    return TelemedicineAppointmentRead.model_validate(appointment_payload(item))


@router.patch("/appointments/{appointment_id}/status", response_model=TelemedicineAppointmentRead, dependencies=[Depends(require_any_permissions("telemedicine.appointment.edit", "telemedicine.queue.view"))])
def update_status(appointment_id: UUID, payload: TelemedicineStatusUpdate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    item = TelemedicineService(db).update_status(appointment_id, payload, user, context)
    db.commit()
    db.refresh(item)
    return TelemedicineAppointmentRead.model_validate(appointment_payload(item))


@router.post("/appointments/{appointment_id}/consent", response_model=TelemedicineAppointmentRead, dependencies=[Depends(require_permissions("telemedicine.appointment.edit"))])
def accept_consent(appointment_id: UUID, payload: TelemedicineConsentUpdate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    item = TelemedicineService(db).accept_consent(appointment_id, payload, user, context)
    db.commit()
    db.refresh(item)
    return TelemedicineAppointmentRead.model_validate(appointment_payload(item))


@router.post("/appointments/{appointment_id}/payment", response_model=TelemedicineAppointmentRead, dependencies=[Depends(require_permissions("telemedicine.payment.view"))])
def update_payment(appointment_id: UUID, payload: TelemedicinePaymentUpdate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    item = TelemedicineService(db).update_payment(appointment_id, payload, user, context)
    db.commit()
    db.refresh(item)
    return TelemedicineAppointmentRead.model_validate(appointment_payload(item))


@router.post("/appointments/{appointment_id}/start", response_model=TelemedicineConsultationRead, dependencies=[Depends(require_permissions("telemedicine.consultation.start"))])
def start_consultation(appointment_id: UUID, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    item = TelemedicineService(db).start_consultation(appointment_id, user, context)
    db.commit()
    db.refresh(item)
    return TelemedicineConsultationRead.model_validate(consultation_payload(item))


@router.get("/consultations", response_model=list[TelemedicineConsultationRead], dependencies=[Depends(require_permissions("telemedicine.view"))])
def list_consultations(status: str | None = None, doctor_id: UUID | None = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    filters = {k: v for k, v in locals().items() if k not in {"user", "db"} and v is not None}
    return [TelemedicineConsultationRead.model_validate(consultation_payload(item)) for item in TelemedicineService(db).list_consultations(user, filters)]


@router.post("/consultations/{consultation_id}/join/{role}", response_model=TelemedicineConsultationRead, dependencies=[Depends(require_permissions("telemedicine.consultation.start"))])
def join_consultation(consultation_id: UUID, role: str, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    item = TelemedicineService(db).join_consultation(consultation_id, role, user, context)
    db.commit()
    db.refresh(item)
    return TelemedicineConsultationRead.model_validate(consultation_payload(item))


@router.put("/consultations/{consultation_id}", response_model=TelemedicineConsultationRead, dependencies=[Depends(require_permissions("telemedicine.prescription.create"))])
def update_consultation(consultation_id: UUID, payload: TelemedicineConsultationUpdate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    item = TelemedicineService(db).update_consultation(consultation_id, payload, user, context)
    db.commit()
    db.refresh(item)
    return TelemedicineConsultationRead.model_validate(consultation_payload(item))


@router.post("/consultations/{consultation_id}/complete", response_model=TelemedicineConsultationRead, dependencies=[Depends(require_permissions("telemedicine.consultation.complete"))])
def complete_consultation(consultation_id: UUID, payload: TelemedicineConsultationUpdate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    item = TelemedicineService(db).complete_consultation(consultation_id, payload, user, context)
    db.commit()
    db.refresh(item)
    return TelemedicineConsultationRead.model_validate(consultation_payload(item))


@router.get("/consultations/{consultation_id}/chat", response_model=list[TelemedicineChatRead], dependencies=[Depends(require_permissions("telemedicine.chat.view"))])
def list_chat(consultation_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return [TelemedicineChatRead.model_validate(chat_payload(item)) for item in TelemedicineService(db).list_chat(consultation_id, user)]


@router.post("/consultations/{consultation_id}/chat", response_model=TelemedicineChatRead, dependencies=[Depends(require_permissions("telemedicine.chat.view"))])
def add_chat(consultation_id: UUID, payload: TelemedicineChatCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    item = TelemedicineService(db).add_chat(consultation_id, payload, user, context)
    db.commit()
    db.refresh(item)
    return TelemedicineChatRead.model_validate(chat_payload(item))


@router.post("/files", response_model=TelemedicineFileRead, dependencies=[Depends(require_permissions("telemedicine.file.upload"))])
def add_file(payload: TelemedicineFileCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    item = TelemedicineService(db).add_file(payload, user, context)
    db.commit()
    db.refresh(item)
    return TelemedicineFileRead.model_validate(file_payload(item))


@router.get("/files", response_model=list[TelemedicineFileRead], dependencies=[Depends(require_permissions("telemedicine.file.view"))])
def list_files(consultation_id: UUID | None = None, appointment_id: UUID | None = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return [TelemedicineFileRead.model_validate(file_payload(item)) for item in TelemedicineService(db).list_files(consultation_id, appointment_id, user)]


@router.post("/consultations/{consultation_id}/investigations", response_model=TelemedicineInvestigationRead, dependencies=[Depends(require_permissions("telemedicine.prescription.create"))])
def create_investigation(consultation_id: UUID, payload: TelemedicineInvestigationCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    item = TelemedicineService(db).create_investigation(consultation_id, payload, user, context)
    db.commit()
    db.refresh(item)
    return item


@router.get("/settings", response_model=list[TelemedicineSettingRead], dependencies=[Depends(require_permissions("telemedicine.settings.manage"))])
def list_settings(user=Depends(get_current_user), db: Session = Depends(get_db)):
    return TelemedicineService(db).list_settings(user)


@router.post("/settings", response_model=TelemedicineSettingRead, dependencies=[Depends(require_permissions("telemedicine.settings.manage"))])
def upsert_setting(payload: TelemedicineSettingCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    item = TelemedicineService(db).upsert_setting(payload, user, context)
    db.commit()
    db.refresh(item)
    return item


@router.get("/reports", response_model=TelemedicineReportRead, dependencies=[Depends(require_permissions("telemedicine.report.view"))])
def reports(report_type: str = Query("online_appointments"), doctor_id: UUID | None = None, status: str | None = None, payment_status: str | None = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    filters = {k: v for k, v in locals().items() if k not in {"user", "db", "report_type"} and v is not None}
    return TelemedicineService(db).reports(user, report_type, filters)
