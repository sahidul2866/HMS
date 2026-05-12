from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_request_context
from app.dependencies.permissions import require_permissions
from app.modules.scanner.service import ScannerService
from app.schemas.scanner import ScanCodeCreate, ScanCodeRead, ScanResolveRequest, ScanResolveResponse, ScanSettingRead, ScanSettingWrite

router = APIRouter(prefix="/scanner", tags=["Scanner"])


@router.post("/resolve", response_model=ScanResolveResponse, dependencies=[Depends(require_permissions("scanner.use"))])
def resolve_scan(payload: ScanResolveRequest, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return ScannerService(db).resolve(payload, user, context)


@router.post("/codes", response_model=ScanCodeRead, dependencies=[Depends(require_permissions("scanner.generate"))])
def create_scan_code(payload: ScanCodeCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return ScannerService(db).create_code(payload, user, context)


@router.get("/settings", response_model=list[ScanSettingRead], dependencies=[Depends(require_permissions("scanner.settings.manage"))])
def list_settings(user=Depends(get_current_user), db: Session = Depends(get_db)):
    return ScannerService(db).list_settings(user)


@router.post("/settings", response_model=ScanSettingRead, dependencies=[Depends(require_permissions("scanner.settings.manage"))])
def upsert_setting(payload: ScanSettingWrite, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return ScannerService(db).upsert_setting(payload, user)

