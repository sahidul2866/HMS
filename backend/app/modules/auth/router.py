from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_current_user_optional, get_request_context
from app.modules.auth.service import AuthService
from app.modules.patient_auth.service import PatientAuthService
from app.schemas.auth import LoginRequest, LoginResponse, LogoutRequest, PatientLoginResponse, PatientRegisterRequest, RefreshRequest
from app.schemas.common import MessageResponse
from app.schemas.user import CurrentUserRead

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, context=Depends(get_request_context), db: Session = Depends(get_db)) -> LoginResponse:
    return AuthService(db).login(payload.username_or_email, payload.password, context)


@router.post("/patient-register", response_model=PatientLoginResponse)
def patient_register(payload: PatientRegisterRequest, context=Depends(get_request_context), db: Session = Depends(get_db)) -> PatientLoginResponse:
    return PatientAuthService(db).register(payload, context)


@router.post("/refresh", response_model=LoginResponse)
def refresh(payload: RefreshRequest, context=Depends(get_request_context), db: Session = Depends(get_db)) -> LoginResponse:
    return AuthService(db).refresh(payload.refresh_token, context)


@router.post("/logout", response_model=MessageResponse)
def logout(
    payload: LogoutRequest,
    context=Depends(get_request_context),
    db: Session = Depends(get_db),
    user=Depends(get_current_user_optional),
) -> MessageResponse:
    AuthService(db).logout(user, payload.refresh_token, context)
    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=CurrentUserRead)
def me(user=Depends(get_current_user), db: Session = Depends(get_db)) -> CurrentUserRead:
    service = AuthService(db)
    refreshed_user = service.repository.get_user_by_id(str(user.id))
    if not refreshed_user:
        return service.to_current_user(user)
    return service.to_current_user(refreshed_user)
