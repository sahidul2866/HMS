from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, JSON, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseModelMixin


class TransportVehicle(Base, BaseModelMixin):
    __tablename__ = "transport_vehicles"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    vehicle_number: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    registration_number: Mapped[str | None] = mapped_column(String(100), unique=True)
    vehicle_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    capacity: Mapped[int | None] = mapped_column()
    equipment_available: Mapped[list | None] = mapped_column(JSON)
    assigned_driver_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("transport_drivers.id"))
    insurance_details: Mapped[str | None] = mapped_column(Text)
    insurance_expiry: Mapped[date | None] = mapped_column(Date())
    fitness_expiry: Mapped[date | None] = mapped_column(Date())
    registration_expiry: Mapped[date | None] = mapped_column(Date())
    fuel_type: Mapped[str | None] = mapped_column(String(40))
    current_status: Mapped[str] = mapped_column(String(40), nullable=False, default="available", index=True)
    current_latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    current_longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7))
    location_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    readiness_status: Mapped[str] = mapped_column(String(40), nullable=False, default="ready")
    readiness_alerts: Mapped[list | None] = mapped_column(JSON)
    qr_code: Mapped[str | None] = mapped_column(String(160), unique=True)
    remarks: Mapped[str | None] = mapped_column(Text)

    branch = relationship("Branch")
    assigned_driver = relationship("TransportDriver", foreign_keys=[assigned_driver_id], post_update=True)


class TransportDriver(Base, BaseModelMixin):
    __tablename__ = "transport_drivers"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    employee_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("hr_employees.id"))
    driver_name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    contact_number: Mapped[str | None] = mapped_column(String(60))
    license_number: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    license_expiry_date: Mapped[date | None] = mapped_column(Date())
    assigned_vehicle_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("transport_vehicles.id"))
    shift: Mapped[str | None] = mapped_column(String(80))
    availability_status: Mapped[str] = mapped_column(String(40), nullable=False, default="available", index=True)
    emergency_contact: Mapped[str | None] = mapped_column(String(120))
    qr_code: Mapped[str | None] = mapped_column(String(160), unique=True)
    remarks: Mapped[str | None] = mapped_column(Text)

    branch = relationship("Branch")
    employee = relationship("HREmployee")
    assigned_vehicle = relationship("TransportVehicle", foreign_keys=[assigned_vehicle_id], post_update=True)


class TransportRequest(Base, BaseModelMixin):
    __tablename__ = "transport_requests"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    request_number: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    request_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    trip_type: Mapped[str | None] = mapped_column(String(80), index=True)
    source_department: Mapped[str | None] = mapped_column(String(100), index=True)
    patient_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"), index=True)
    staff_employee_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("hr_employees.id"))
    unknown_patient_name: Mapped[str | None] = mapped_column(String(160))
    pickup_location: Mapped[str] = mapped_column(String(255), nullable=False)
    dropoff_location: Mapped[str] = mapped_column(String(255), nullable=False)
    required_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    urgency: Mapped[str] = mapped_column(String(40), nullable=False, default="routine", index=True)
    priority: Mapped[str] = mapped_column(String(40), nullable=False, default="normal", index=True)
    reason: Mapped[str | None] = mapped_column(Text)
    required_vehicle_type: Mapped[str | None] = mapped_column(String(80))
    required_equipment: Mapped[list | None] = mapped_column(JSON)
    attendant_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requested_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    transfer_reason: Mapped[str | None] = mapped_column(Text)
    patient_condition: Mapped[str | None] = mapped_column(Text)
    required_support: Mapped[str | None] = mapped_column(Text)
    transfer_notes: Mapped[str | None] = mapped_column(Text)
    receiving_facility: Mapped[str | None] = mapped_column(String(180))
    responsible_doctor: Mapped[str | None] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(60), nullable=False, default="requested", index=True)
    assigned_vehicle_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("transport_vehicles.id"))
    assigned_driver_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("transport_drivers.id"))
    billing_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    billing_status: Mapped[str] = mapped_column(String(40), nullable=False, default="not_required")
    billing_invoice_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("billing_invoices.id"))
    override_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    override_reason: Mapped[str | None] = mapped_column(Text)
    remarks: Mapped[str | None] = mapped_column(Text)

    branch = relationship("Branch")
    patient = relationship("Patient")
    staff_employee = relationship("HREmployee")
    requested_by = relationship("User")
    assigned_vehicle = relationship("TransportVehicle")
    assigned_driver = relationship("TransportDriver")
    billing_invoice = relationship("BillingInvoice")


class TransportTrip(Base, BaseModelMixin):
    __tablename__ = "transport_trips"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    request_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("transport_requests.id"), index=True)
    trip_number: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    vehicle_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("transport_vehicles.id"), nullable=False, index=True)
    driver_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("transport_drivers.id"), nullable=False, index=True)
    patient_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("patients.id"), index=True)
    staff_employee_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("hr_employees.id"))
    pickup_location: Mapped[str] = mapped_column(String(255), nullable=False)
    dropoff_location: Mapped[str] = mapped_column(String(255), nullable=False)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    distance_km: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    waiting_minutes: Mapped[int] = mapped_column(nullable=False, default=0)
    trip_type: Mapped[str | None] = mapped_column(String(80), index=True)
    priority: Mapped[str] = mapped_column(String(40), nullable=False, default="normal")
    status: Mapped[str] = mapped_column(String(60), nullable=False, default="vehicle_assigned", index=True)
    location_updates: Mapped[list | None] = mapped_column(JSON)
    charges: Mapped[dict | None] = mapped_column(JSON)
    billing_status: Mapped[str] = mapped_column(String(40), nullable=False, default="not_required")
    billing_invoice_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("billing_invoices.id"))
    completed_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    qr_code: Mapped[str | None] = mapped_column(String(160), unique=True)
    remarks: Mapped[str | None] = mapped_column(Text)

    branch = relationship("Branch")
    request = relationship("TransportRequest")
    vehicle = relationship("TransportVehicle")
    driver = relationship("TransportDriver")
    patient = relationship("Patient")
    staff_employee = relationship("HREmployee")
    billing_invoice = relationship("BillingInvoice")
    completed_by = relationship("User")


class TransportSchedule(Base, BaseModelMixin):
    __tablename__ = "transport_schedules"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    vehicle_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("transport_vehicles.id"))
    driver_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("transport_drivers.id"))
    schedule_type: Mapped[str] = mapped_column(String(60), nullable=False, default="booking")
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    recurrence_rule: Mapped[str | None] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="scheduled")
    purpose: Mapped[str | None] = mapped_column(String(180))
    remarks: Mapped[str | None] = mapped_column(Text)

    branch = relationship("Branch")
    vehicle = relationship("TransportVehicle")
    driver = relationship("TransportDriver")


class TransportMaintenance(Base, BaseModelMixin):
    __tablename__ = "transport_maintenance"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    vehicle_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("transport_vehicles.id"), nullable=False, index=True)
    maintenance_type: Mapped[str] = mapped_column(String(80), nullable=False)
    service_date: Mapped[date] = mapped_column(Date(), nullable=False, index=True)
    odometer_reading: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    workshop_vendor: Mapped[str | None] = mapped_column(String(180))
    cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    next_service_date: Mapped[date | None] = mapped_column(Date(), index=True)
    parts_changed: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="completed")
    remarks: Mapped[str | None] = mapped_column(Text)

    branch = relationship("Branch")
    vehicle = relationship("TransportVehicle")


class TransportFuelLog(Base, BaseModelMixin):
    __tablename__ = "transport_fuel_logs"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    vehicle_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("transport_vehicles.id"), nullable=False, index=True)
    fuel_date: Mapped[date] = mapped_column(Date(), nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=0)
    fuel_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    odometer_reading: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    filled_by: Mapped[str | None] = mapped_column(String(160))
    receipt_attachment: Mapped[str | None] = mapped_column(String(255))
    expense_category: Mapped[str] = mapped_column(String(60), nullable=False, default="fuel")
    remarks: Mapped[str | None] = mapped_column(Text)

    branch = relationship("Branch")
    vehicle = relationship("TransportVehicle")


class TransportSetting(Base, BaseModelMixin):
    __tablename__ = "transport_settings"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    setting_key: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    setting_value: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    meta: Mapped[dict | None] = mapped_column(JSON)

    branch = relationship("Branch")
