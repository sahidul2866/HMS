from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


def _blank_to_none(data: Any, keys: tuple[str, ...]) -> Any:
    if isinstance(data, dict):
        for key in keys:
            if data.get(key) in {"", "null", "undefined"}:
                data[key] = None
    return data


class TransportDashboardRead(BaseModel):
    total_vehicles: int = 0
    available_ambulances: int = 0
    available_drivers: int = 0
    active_trips: int = 0
    pending_requests: int = 0
    emergency_requests: int = 0
    completed_trips_today: int = 0
    vehicles_under_maintenance: int = 0
    fuel_expense_today: Decimal = Decimal("0")
    delayed_trips: int = 0
    upcoming_scheduled_trips: int = 0
    readiness_alerts: int = 0
    by_vehicle_type: dict[str, int] = {}
    by_trip_status: dict[str, int] = {}
    by_priority: dict[str, int] = {}


class TransportVehicleCreate(BaseModel):
    vehicle_number: str = Field(min_length=1, max_length=80)
    registration_number: str | None = None
    vehicle_type: str
    capacity: int | None = None
    equipment_available: list[str] = []
    assigned_driver_id: UUID | None = None
    insurance_details: str | None = None
    insurance_expiry: date | None = None
    fitness_expiry: date | None = None
    registration_expiry: date | None = None
    fuel_type: str | None = None
    current_status: str = "available"
    remarks: str | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize(cls, data: Any) -> Any:
        return _blank_to_none(data, ("assigned_driver_id", "insurance_expiry", "fitness_expiry", "registration_expiry"))


class TransportVehicleRead(TransportVehicleCreate):
    id: UUID
    branch_id: UUID | None = None
    assigned_driver_name: str | None = None
    current_latitude: Decimal | None = None
    current_longitude: Decimal | None = None
    location_updated_at: datetime | None = None
    readiness_status: str
    readiness_alerts: list[str] = []
    qr_code: str | None = None
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class TransportDriverCreate(BaseModel):
    employee_id: UUID | None = None
    driver_name: str = Field(min_length=2, max_length=160)
    contact_number: str | None = None
    license_number: str
    license_expiry_date: date | None = None
    assigned_vehicle_id: UUID | None = None
    shift: str | None = None
    availability_status: str = "available"
    emergency_contact: str | None = None
    remarks: str | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize(cls, data: Any) -> Any:
        return _blank_to_none(data, ("employee_id", "assigned_vehicle_id", "license_expiry_date"))


class TransportDriverRead(TransportDriverCreate):
    id: UUID
    branch_id: UUID | None = None
    assigned_vehicle_number: str | None = None
    employee_code: str | None = None
    license_alert: str | None = None
    qr_code: str | None = None
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class TransportRequestCreate(BaseModel):
    request_type: str
    trip_type: str | None = None
    source_department: str | None = None
    patient_id: UUID | None = None
    staff_employee_id: UUID | None = None
    unknown_patient_name: str | None = None
    pickup_location: str = Field(min_length=1, max_length=255)
    dropoff_location: str = Field(min_length=1, max_length=255)
    required_at: datetime | None = None
    urgency: str = "routine"
    priority: str = "normal"
    reason: str | None = None
    required_vehicle_type: str | None = None
    required_equipment: list[str] = []
    attendant_required: bool = False
    transfer_reason: str | None = None
    patient_condition: str | None = None
    required_support: str | None = None
    transfer_notes: str | None = None
    receiving_facility: str | None = None
    responsible_doctor: str | None = None
    billing_required: bool = False
    remarks: str | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize(cls, data: Any) -> Any:
        return _blank_to_none(data, ("patient_id", "staff_employee_id", "required_at"))


class TransportRequestRead(TransportRequestCreate):
    id: UUID
    branch_id: UUID | None = None
    request_number: str
    patient_name: str | None = None
    patient_number: str | None = None
    staff_name: str | None = None
    requested_by_name: str | None = None
    status: str
    assigned_vehicle_id: UUID | None = None
    assigned_vehicle_number: str | None = None
    assigned_driver_id: UUID | None = None
    assigned_driver_name: str | None = None
    billing_status: str
    billing_invoice_id: UUID | None = None
    override_used: bool
    override_reason: str | None = None
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class TransportDispatchRequest(BaseModel):
    vehicle_id: UUID
    driver_id: UUID
    scheduled_at: datetime | None = None
    override: bool = False
    override_reason: str | None = None
    remarks: str | None = None


class TransportTripStatusUpdate(BaseModel):
    status: str
    start_time: datetime | None = None
    end_time: datetime | None = None
    distance_km: Decimal | None = None
    waiting_minutes: int | None = None
    charges: dict[str, Any] | None = None
    billing_status: str | None = None
    remarks: str | None = None


class TransportLocationUpdate(BaseModel):
    latitude: Decimal
    longitude: Decimal
    source: str = "manual"
    recorded_at: datetime | None = None
    remarks: str | None = None


class TransportTripRead(BaseModel):
    id: UUID
    branch_id: UUID | None = None
    request_id: UUID | None = None
    request_number: str | None = None
    trip_number: str
    vehicle_id: UUID
    vehicle_number: str | None = None
    driver_id: UUID
    driver_name: str | None = None
    patient_id: UUID | None = None
    patient_name: str | None = None
    patient_number: str | None = None
    staff_employee_id: UUID | None = None
    staff_name: str | None = None
    pickup_location: str
    dropoff_location: str
    scheduled_at: datetime | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    distance_km: Decimal
    waiting_minutes: int
    trip_type: str | None = None
    priority: str
    status: str
    location_updates: list[dict[str, Any]] = []
    charges: dict[str, Any] | None = None
    billing_status: str
    billing_invoice_id: UUID | None = None
    completed_by_name: str | None = None
    completed_at: datetime | None = None
    qr_code: str | None = None
    remarks: str | None = None
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class TransportScheduleCreate(BaseModel):
    vehicle_id: UUID | None = None
    driver_id: UUID | None = None
    schedule_type: str = "booking"
    start_at: datetime
    end_at: datetime
    recurrence_rule: str | None = None
    status: str = "scheduled"
    purpose: str | None = None
    remarks: str | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize(cls, data: Any) -> Any:
        return _blank_to_none(data, ("vehicle_id", "driver_id"))


class TransportScheduleRead(TransportScheduleCreate):
    id: UUID
    vehicle_number: str | None = None
    driver_name: str | None = None
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class TransportMaintenanceCreate(BaseModel):
    vehicle_id: UUID
    maintenance_type: str
    service_date: date
    odometer_reading: Decimal | None = None
    workshop_vendor: str | None = None
    cost: Decimal = Decimal("0")
    next_service_date: date | None = None
    parts_changed: str | None = None
    status: str = "completed"
    remarks: str | None = None


class TransportMaintenanceRead(TransportMaintenanceCreate):
    id: UUID
    vehicle_number: str | None = None
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class TransportFuelLogCreate(BaseModel):
    vehicle_id: UUID
    fuel_date: date
    quantity: Decimal = Decimal("0")
    fuel_cost: Decimal = Decimal("0")
    odometer_reading: Decimal | None = None
    filled_by: str | None = None
    receipt_attachment: str | None = None
    expense_category: str = "fuel"
    remarks: str | None = None


class TransportFuelLogRead(TransportFuelLogCreate):
    id: UUID
    vehicle_number: str | None = None
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class TransportSettingCreate(BaseModel):
    setting_key: str = Field(min_length=2, max_length=120)
    setting_value: str
    description: str | None = None
    meta: dict[str, Any] | None = None


class TransportSettingRead(TransportSettingCreate):
    id: UUID
    is_active: bool
    model_config = {"from_attributes": True}


class TransportReportRead(BaseModel):
    report_type: str
    filters: dict[str, Any]
    rows: list[dict[str, Any]]
    totals: dict[str, Any]
