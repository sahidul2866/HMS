from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_request_context
from app.dependencies.integration import verify_machine_integration_key
from app.dependencies.permissions import require_any_permissions
from app.modules.lis.schemas import (
    LISMachineRead,
    LISMachineResultIngest,
    LISMachineResultIngestResponse,
    LISSimulationRequest,
    LISSimulationResult,
    LISWorkItemRead,
)
from app.modules.lis.service import LISService

router = APIRouter(prefix="/lis", tags=["LIS"])


@router.get(
    "/machines",
    response_model=list[LISMachineRead],
    dependencies=[Depends(require_any_permissions("laboratory.view", "laboratory.manage"))],
)
def list_lis_machines(db: Session = Depends(get_db)) -> list[LISMachineRead]:
    return LISService(db).list_machines()


@router.get(
    "/queue",
    response_model=list[LISWorkItemRead],
    dependencies=[Depends(require_any_permissions("laboratory.view", "laboratory.manage"))],
)
def list_lis_queue(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[LISWorkItemRead]:
    return LISService(db).list_queue(user)


@router.post(
    "/simulate-analyze",
    response_model=LISSimulationResult,
    dependencies=[Depends(require_any_permissions("laboratory.manage", "settings.role.manage"))],
)
def simulate_lis_analyze(
    payload: LISSimulationRequest,
    context=Depends(get_request_context),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LISSimulationResult:
    return LISService(db).simulate_analysis(payload, user, context)


@router.post(
    "/integration/results",
    response_model=LISMachineResultIngestResponse,
    dependencies=[Depends(verify_machine_integration_key)],
)
def ingest_machine_result(
    payload: LISMachineResultIngest,
    context=Depends(get_request_context),
    db: Session = Depends(get_db),
) -> LISMachineResultIngestResponse:
    return LISService(db).ingest_machine_result(payload, actor=None, context=context)
