from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_patient_account, get_request_context
from app.modules.patient_auth.service import PatientAuthService
from app.schemas.auth import LoginRequest, LogoutRequest, PatientLoginResponse, PatientRegisterRequest, RefreshRequest

router = APIRouter(prefix="/patient-auth", tags=["Patient Auth"])


@router.post("/login", response_model=PatientLoginResponse)
def patient_login(payload: LoginRequest, context=Depends(get_request_context), db: Session = Depends(get_db)) -> PatientLoginResponse:
    return PatientAuthService(db).login(payload.username_or_email, payload.password, context)


@router.post("/register", response_model=PatientLoginResponse)
def patient_register(payload: PatientRegisterRequest, context=Depends(get_request_context), db: Session = Depends(get_db)) -> PatientLoginResponse:
    return PatientAuthService(db).register(payload, context)


@router.post("/refresh", response_model=PatientLoginResponse)
def patient_refresh(payload: RefreshRequest, context=Depends(get_request_context), db: Session = Depends(get_db)) -> PatientLoginResponse:
    return PatientAuthService(db).refresh(payload.refresh_token, context)


@router.post("/logout")
def patient_logout(payload: LogoutRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    PatientAuthService(db).logout(payload.refresh_token)
    return {"status": "ok"}


@router.get("/me")
def patient_me(account=Depends(get_current_patient_account), db: Session = Depends(get_db)):
    return PatientAuthService(db).to_current_patient(account)
