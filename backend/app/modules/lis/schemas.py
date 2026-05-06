from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class LISMachineRead(BaseModel):
    code: str
    name: str
    analyzer_type: str
    protocol: str
    host: str
    port: int
    status: str


class LISWorkItemRead(BaseModel):
    order_id: UUID
    visit_number: str
    patient_number: str
    patient_name: str
    item_name: str
    status: str


class LISSimulationRequest(BaseModel):
    machine_code: str = Field(min_length=2, max_length=60)
    order_id: UUID


class LISAnalyteResult(BaseModel):
    code: str
    name: str
    value: str
    unit: str | None = None
    reference_range: str | None = None
    flag: str = "normal"


class LISSimulationResult(BaseModel):
    order_id: UUID
    machine_code: str
    machine_name: str
    generated_result: str
    sample_barcode: str
    analytes: list[LISAnalyteResult]
    completed_at: datetime


class LISMachineResultIngest(BaseModel):
    machine_code: str = Field(min_length=2, max_length=60)
    order_id: UUID
    sample_barcode: str | None = None
    analytes: list[LISAnalyteResult]
    sample_note: str | None = None


class LISMachineResultIngestResponse(BaseModel):
    order_id: UUID
    machine_code: str
    sample_barcode: str
    saved: bool = True
