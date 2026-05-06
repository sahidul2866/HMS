from datetime import UTC, datetime
from types import SimpleNamespace

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.exceptions import AppException
from app.models.user import User
from app.modules.laboratory.service import LaboratoryService
from app.modules.lis.schemas import (
    LISAnalyteResult,
    LISMachineRead,
    LISMachineResultIngest,
    LISMachineResultIngestResponse,
    LISSimulationRequest,
    LISSimulationResult,
    LISWorkItemRead,
)
from app.schemas.encounter import ClinicalInvestigationResultUpdate


class LISService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.laboratory_service = LaboratoryService(db)

    def list_machines(self) -> list[LISMachineRead]:
        return [
            LISMachineRead(
                code="XN_1000",
                name="Sysmex XN-1000",
                analyzer_type="Hematology",
                protocol="HL7/ASTM",
                host="192.168.0.110",
                port=5001,
                status="online",
            ),
            LISMachineRead(
                code="ATELICA_SOLUTION",
                name="Siemens Atellica Solution",
                analyzer_type="Chemistry/Immunoassay",
                protocol="HL7",
                host="192.168.0.111",
                port=5002,
                status="online",
            ),
            LISMachineRead(
                code="URISED_3",
                name="UriSed 3 Pro",
                analyzer_type="Urine Sediment",
                protocol="ASTM",
                host="192.168.0.112",
                port=5003,
                status="standby",
            ),
        ]

    def list_queue(self, actor: User) -> list[LISWorkItemRead]:
        worklist = self.laboratory_service.list_worklist(actor)
        queue_status = {"pending", "collected", "in_progress"}
        return [
            LISWorkItemRead(
                order_id=item.order_id,
                visit_number=item.visit_number,
                patient_number=item.patient_number,
                patient_name=item.patient_name,
                item_name=item.item_name,
                status=item.status,
            )
            for item in worklist
            if item.status in queue_status
        ]

    def simulate_analysis(
        self,
        payload: LISSimulationRequest,
        actor: User,
        context: dict[str, str | None],
    ) -> LISSimulationResult:
        machines = {machine.code: machine for machine in self.list_machines()}
        machine = machines.get(payload.machine_code)
        if not machine:
            raise AppException(404, "lis_machine_not_found", f"Machine {payload.machine_code} not found")
        if machine.status == "offline":
            raise AppException(409, "lis_machine_offline", f"Machine {machine.name} is offline")

        analytes = self._build_analytes(machine.code)
        generated_result = self._format_result_text(analytes)
        sample_barcode = f"{machine.code[:3]}-{str(payload.order_id).split('-')[0].upper()}"
        self.ingest_machine_result(
            LISMachineResultIngest(
                machine_code=machine.code,
                order_id=payload.order_id,
                sample_barcode=sample_barcode,
                analytes=analytes,
                sample_note=f"Completed on {machine.name} ({machine.protocol})",
            ),
            actor,
            context,
        )

        completed_at = datetime.now(UTC)
        return LISSimulationResult(
            order_id=payload.order_id,
            machine_code=machine.code,
            machine_name=machine.name,
            generated_result=generated_result,
            sample_barcode=sample_barcode,
            analytes=analytes,
            completed_at=completed_at,
        )

    def ingest_machine_result(
        self,
        payload: LISMachineResultIngest,
        actor: User | None,
        context: dict[str, str | None],
    ) -> LISMachineResultIngestResponse:
        generated_result = self._format_result_text(payload.analytes)
        barcode = payload.sample_barcode or f"{payload.machine_code[:3]}-{str(payload.order_id).split('-')[0].upper()}"
        resolved_actor = actor or self._resolve_machine_actor()
        self.laboratory_service.update_result(
            payload.order_id,
            ClinicalInvestigationResultUpdate(
                status="completed",
                sample_note=f"{payload.sample_note or 'Machine result imported'} | Barcode: {barcode}",
                result_text=generated_result,
            ),
            resolved_actor,
            context,
        )
        return LISMachineResultIngestResponse(
            order_id=payload.order_id,
            machine_code=payload.machine_code,
            sample_barcode=barcode,
        )

    @staticmethod
    def _build_analytes(machine_code: str) -> list[LISAnalyteResult]:
        machine_profiles: dict[str, list[LISAnalyteResult]] = {
            "XN_1000": [
                LISAnalyteResult(code="WBC", name="White Blood Cell", value="7.4", unit="x10^3/uL", reference_range="4.0-11.0"),
                LISAnalyteResult(code="RBC", name="Red Blood Cell", value="4.90", unit="x10^6/uL", reference_range="4.2-5.9"),
                LISAnalyteResult(code="HGB", name="Hemoglobin", value="13.6", unit="g/dL", reference_range="12.0-16.0"),
                LISAnalyteResult(code="PLT", name="Platelet", value="238", unit="x10^3/uL", reference_range="150-450"),
            ],
            "ATELICA_SOLUTION": [
                LISAnalyteResult(code="GLU", name="Glucose", value="96", unit="mg/dL", reference_range="70-110"),
                LISAnalyteResult(code="CRE", name="Creatinine", value="0.9", unit="mg/dL", reference_range="0.6-1.3"),
                LISAnalyteResult(code="ALT", name="ALT", value="28", unit="U/L", reference_range="7-56"),
                LISAnalyteResult(code="TSH", name="TSH", value="2.1", unit="uIU/mL", reference_range="0.4-4.0"),
            ],
            "URISED_3": [
                LISAnalyteResult(code="URBC", name="Urine RBC", value="0-2", unit="/hpf", reference_range="0-2"),
                LISAnalyteResult(code="UWBC", name="Urine WBC", value="0-3", unit="/hpf", reference_range="0-5"),
                LISAnalyteResult(code="CAST", name="Casts", value="Not detected", reference_range="Not detected"),
                LISAnalyteResult(code="CRYS", name="Crystals", value="Not detected", reference_range="Not detected"),
            ],
        }
        return machine_profiles.get(
            machine_code,
            [LISAnalyteResult(code="GEN", name="General Result", value="Within normal limits", flag="normal")],
        )

    @staticmethod
    def _format_result_text(analytes: list[LISAnalyteResult]) -> str:
        lines = [
            f"{row.code}: {row.value}{f' {row.unit}' if row.unit else ''} (Ref: {row.reference_range})"
            if row.reference_range
            else f"{row.code}: {row.value}{f' {row.unit}' if row.unit else ''}"
            for row in analytes
        ]
        return "\n".join(lines)

    def _resolve_machine_actor(self) -> User:
        user = self.db.execute(select(User).where(User.is_active.is_(True)).order_by(User.created_at.asc())).scalars().first()
        if not user:
            raise AppException(500, "machine_actor_not_found", "No active user found for machine integration")
        return SimpleNamespace(id=user.id, branch_id=None)  # type: ignore[return-value]
