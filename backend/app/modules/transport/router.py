from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user, get_request_context
from app.dependencies.permissions import require_any_permissions, require_permissions
from app.modules.transport.service import TransportService
from app.schemas.transport import (
    TransportDashboardRead,
    TransportDispatchRequest,
    TransportDriverCreate,
    TransportDriverRead,
    TransportFuelLogCreate,
    TransportFuelLogRead,
    TransportLocationUpdate,
    TransportMaintenanceCreate,
    TransportMaintenanceRead,
    TransportReportRead,
    TransportRequestCreate,
    TransportRequestRead,
    TransportScheduleCreate,
    TransportScheduleRead,
    TransportSettingCreate,
    TransportSettingRead,
    TransportTripRead,
    TransportTripStatusUpdate,
    TransportVehicleCreate,
    TransportVehicleRead,
)

router = APIRouter(prefix="/transport", tags=["Transport"])


def vehicle_payload(item) -> dict:
    data = {column.name: getattr(item, column.name) for column in item.__table__.columns}
    data["assigned_driver_name"] = item.assigned_driver.driver_name if item.assigned_driver else None
    data["readiness_alerts"] = item.readiness_alerts or []
    data["equipment_available"] = item.equipment_available or []
    return data


def driver_payload(item) -> dict:
    data = {column.name: getattr(item, column.name) for column in item.__table__.columns}
    data["assigned_vehicle_number"] = item.assigned_vehicle.vehicle_number if item.assigned_vehicle else None
    data["employee_code"] = item.employee.staff_code if item.employee and hasattr(item.employee, "staff_code") else None
    data["license_alert"] = f"License expires on {item.license_expiry_date.isoformat()}" if item.license_expiry_date else None
    return data


def request_payload(item) -> dict:
    data = {column.name: getattr(item, column.name) for column in item.__table__.columns}
    data["patient_name"] = f"{item.patient.first_name} {item.patient.last_name}".strip() if item.patient else None
    data["patient_number"] = item.patient.patient_number if item.patient else None
    data["staff_name"] = item.staff_employee.full_name if item.staff_employee else None
    data["requested_by_name"] = item.requested_by.full_name if item.requested_by else None
    data["assigned_vehicle_number"] = item.assigned_vehicle.vehicle_number if item.assigned_vehicle else None
    data["assigned_driver_name"] = item.assigned_driver.driver_name if item.assigned_driver else None
    data["required_equipment"] = item.required_equipment or []
    return data


def trip_payload(item) -> dict:
    data = {column.name: getattr(item, column.name) for column in item.__table__.columns}
    data["request_number"] = item.request.request_number if item.request else None
    data["vehicle_number"] = item.vehicle.vehicle_number if item.vehicle else None
    data["driver_name"] = item.driver.driver_name if item.driver else None
    data["patient_name"] = f"{item.patient.first_name} {item.patient.last_name}".strip() if item.patient else None
    data["patient_number"] = item.patient.patient_number if item.patient else None
    data["staff_name"] = item.staff_employee.full_name if item.staff_employee else None
    data["completed_by_name"] = item.completed_by.full_name if item.completed_by else None
    data["location_updates"] = item.location_updates or []
    return data


def schedule_payload(item) -> dict:
    data = {column.name: getattr(item, column.name) for column in item.__table__.columns}
    data["vehicle_number"] = item.vehicle.vehicle_number if item.vehicle else None
    data["driver_name"] = item.driver.driver_name if item.driver else None
    return data


def vehicle_log_payload(item) -> dict:
    data = {column.name: getattr(item, column.name) for column in item.__table__.columns}
    data["vehicle_number"] = item.vehicle.vehicle_number if item.vehicle else None
    return data


@router.get("/dashboard", response_model=TransportDashboardRead, dependencies=[Depends(require_permissions("transport.dashboard.view"))])
def dashboard(
    vehicle_type: str | None = None,
    status: str | None = None,
    driver_id: UUID | None = None,
    department: str | None = None,
    trip_type: str | None = None,
    date_filter: date | None = Query(default=None, alias="date"),
    priority: str | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    filters = {k: v for k, v in {"vehicle_type": vehicle_type, "status": status, "driver_id": driver_id, "department": department, "trip_type": trip_type, "date": date_filter, "priority": priority}.items() if v is not None}
    return TransportService(db).dashboard(user, filters)


@router.get("/vehicles", response_model=list[TransportVehicleRead], dependencies=[Depends(require_permissions("transport.view"))])
def list_vehicles(vehicle_type: str | None = None, status: str | None = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return [TransportVehicleRead.model_validate(vehicle_payload(item)) for item in TransportService(db).list_vehicles(user, {"vehicle_type": vehicle_type, "status": status})]


@router.post("/vehicles", response_model=TransportVehicleRead, dependencies=[Depends(require_permissions("transport.vehicle.create"))])
def create_vehicle(payload: TransportVehicleCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    item = TransportService(db).create_vehicle(payload, user, context)
    db.commit()
    db.refresh(item)
    return TransportVehicleRead.model_validate(vehicle_payload(item))


@router.put("/vehicles/{vehicle_id}", response_model=TransportVehicleRead, dependencies=[Depends(require_permissions("transport.vehicle.edit"))])
def update_vehicle(vehicle_id: UUID, payload: TransportVehicleCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    item = TransportService(db).update_vehicle(vehicle_id, payload, user, context)
    db.commit()
    db.refresh(item)
    return TransportVehicleRead.model_validate(vehicle_payload(item))


@router.get("/drivers", response_model=list[TransportDriverRead], dependencies=[Depends(require_permissions("transport.view"))])
def list_drivers(status: str | None = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return [TransportDriverRead.model_validate(driver_payload(item)) for item in TransportService(db).list_drivers(user, {"status": status})]


@router.post("/drivers", response_model=TransportDriverRead, dependencies=[Depends(require_permissions("transport.driver.manage"))])
def create_driver(payload: TransportDriverCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    item = TransportService(db).create_driver(payload, user, context)
    db.commit()
    db.refresh(item)
    return TransportDriverRead.model_validate(driver_payload(item))


@router.put("/drivers/{driver_id}", response_model=TransportDriverRead, dependencies=[Depends(require_permissions("transport.driver.manage"))])
def update_driver(driver_id: UUID, payload: TransportDriverCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    item = TransportService(db).update_driver(driver_id, payload, user, context)
    db.commit()
    db.refresh(item)
    return TransportDriverRead.model_validate(driver_payload(item))


@router.get("/requests", response_model=list[TransportRequestRead], dependencies=[Depends(require_permissions("transport.view"))])
def list_requests(status: str | None = None, priority: str | None = None, trip_type: str | None = None, department: str | None = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    filters = {k: v for k, v in locals().items() if k not in {"user", "db"} and v is not None}
    return [TransportRequestRead.model_validate(request_payload(item)) for item in TransportService(db).list_requests(user, filters)]


@router.post("/requests", response_model=TransportRequestRead, dependencies=[Depends(require_permissions("transport.request.create"))])
def create_request(payload: TransportRequestCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    item = TransportService(db).create_request(payload, user, context)
    db.commit()
    db.refresh(item)
    return TransportRequestRead.model_validate(request_payload(item))


@router.post("/requests/emergency", response_model=TransportRequestRead, dependencies=[Depends(require_permissions("transport.request.create"))])
def quick_emergency(payload: TransportRequestCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    item = TransportService(db).create_request(payload, user, context, quick_emergency=True)
    db.commit()
    db.refresh(item)
    return TransportRequestRead.model_validate(request_payload(item))


@router.post("/requests/{request_id}/dispatch", response_model=TransportTripRead, dependencies=[Depends(require_permissions("transport.dispatch"))])
def dispatch(request_id: UUID, payload: TransportDispatchRequest, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    item = TransportService(db).dispatch(request_id, payload, user, context)
    db.commit()
    db.refresh(item)
    return TransportTripRead.model_validate(trip_payload(item))


@router.get("/trips", response_model=list[TransportTripRead], dependencies=[Depends(require_permissions("transport.view"))])
def list_trips(status: str | None = None, trip_type: str | None = None, vehicle_id: UUID | None = None, driver_id: UUID | None = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    filters = {k: v for k, v in locals().items() if k not in {"user", "db"} and v is not None}
    return [TransportTripRead.model_validate(trip_payload(item)) for item in TransportService(db).list_trips(user, filters)]


@router.patch("/trips/{trip_id}/status", response_model=TransportTripRead, dependencies=[Depends(require_any_permissions("transport.trip.update", "transport.trip.complete", "transport.trip.cancel"))])
def update_trip_status(trip_id: UUID, payload: TransportTripStatusUpdate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    item = TransportService(db).update_trip_status(trip_id, payload, user, context)
    db.commit()
    db.refresh(item)
    return TransportTripRead.model_validate(trip_payload(item))


@router.post("/trips/{trip_id}/location", response_model=TransportTripRead, dependencies=[Depends(require_permissions("transport.trip.update"))])
def update_location(trip_id: UUID, payload: TransportLocationUpdate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    item = TransportService(db).update_location(trip_id, payload, user, context)
    db.commit()
    db.refresh(item)
    return TransportTripRead.model_validate(trip_payload(item))


@router.get("/schedules", response_model=list[TransportScheduleRead], dependencies=[Depends(require_permissions("transport.view"))])
def list_schedules(user=Depends(get_current_user), db: Session = Depends(get_db)):
    return [TransportScheduleRead.model_validate(schedule_payload(item)) for item in TransportService(db).list_schedules(user)]


@router.post("/schedules", response_model=TransportScheduleRead, dependencies=[Depends(require_permissions("transport.dispatch"))])
def create_schedule(payload: TransportScheduleCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    item = TransportService(db).create_schedule(payload, user, context)
    db.commit()
    db.refresh(item)
    return TransportScheduleRead.model_validate(schedule_payload(item))


@router.get("/maintenance", response_model=list[TransportMaintenanceRead], dependencies=[Depends(require_permissions("transport.maintenance.manage"))])
def list_maintenance(user=Depends(get_current_user), db: Session = Depends(get_db)):
    return [TransportMaintenanceRead.model_validate(vehicle_log_payload(item)) for item in TransportService(db).list_maintenance(user)]


@router.post("/maintenance", response_model=TransportMaintenanceRead, dependencies=[Depends(require_permissions("transport.maintenance.manage"))])
def create_maintenance(payload: TransportMaintenanceCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    item = TransportService(db).create_maintenance(payload, user, context)
    db.commit()
    db.refresh(item)
    return TransportMaintenanceRead.model_validate(vehicle_log_payload(item))


@router.get("/fuel-logs", response_model=list[TransportFuelLogRead], dependencies=[Depends(require_permissions("transport.fuel.manage"))])
def list_fuel_logs(user=Depends(get_current_user), db: Session = Depends(get_db)):
    return [TransportFuelLogRead.model_validate(vehicle_log_payload(item)) for item in TransportService(db).list_fuel_logs(user)]


@router.post("/fuel-logs", response_model=TransportFuelLogRead, dependencies=[Depends(require_permissions("transport.fuel.manage"))])
def create_fuel_log(payload: TransportFuelLogCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    item = TransportService(db).create_fuel_log(payload, user, context)
    db.commit()
    db.refresh(item)
    return TransportFuelLogRead.model_validate(vehicle_log_payload(item))


@router.get("/settings", response_model=list[TransportSettingRead], dependencies=[Depends(require_permissions("transport.settings.manage"))])
def list_settings(user=Depends(get_current_user), db: Session = Depends(get_db)):
    return TransportService(db).list_settings(user)


@router.post("/settings", response_model=TransportSettingRead, dependencies=[Depends(require_permissions("transport.settings.manage"))])
def upsert_setting(payload: TransportSettingCreate, context=Depends(get_request_context), user=Depends(get_current_user), db: Session = Depends(get_db)):
    item = TransportService(db).upsert_setting(payload, user, context)
    db.commit()
    db.refresh(item)
    return item


@router.get("/reports", response_model=TransportReportRead, dependencies=[Depends(require_permissions("transport.report.view"))])
def reports(report_type: str = Query("trip_history"), status: str | None = None, trip_type: str | None = None, vehicle_id: UUID | None = None, driver_id: UUID | None = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    filters = {k: v for k, v in locals().items() if k not in {"user", "db", "report_type"} and v is not None}
    return TransportService(db).reports(user, report_type, filters)
