from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import AppException
from app.models.hr import HREmployee
from app.models.patient import Patient
from app.models.transport import (
    TransportDriver,
    TransportFuelLog,
    TransportMaintenance,
    TransportRequest,
    TransportSchedule,
    TransportSetting,
    TransportTrip,
    TransportVehicle,
)
from app.models.user import User
from app.modules.audit.service import AuditService
from app.schemas.transport import (
    TransportDashboardRead,
    TransportDispatchRequest,
    TransportDriverCreate,
    TransportFuelLogCreate,
    TransportLocationUpdate,
    TransportMaintenanceCreate,
    TransportReportRead,
    TransportRequestCreate,
    TransportScheduleCreate,
    TransportSettingCreate,
    TransportTripStatusUpdate,
    TransportVehicleCreate,
)


AMBULANCE_TYPES = {"ambulance", "icu_ambulance", "basic_life_support_ambulance", "advanced_life_support_ambulance"}
ACTIVE_TRIP_STATUSES = {"vehicle_assigned", "driver_assigned", "dispatched", "arrived_at_pickup", "patient_picked_up", "in_transit", "arrived_at_destination", "delayed"}
NON_DISPATCHABLE_VEHICLE_STATUSES = {"under_maintenance", "out_of_service", "cleaning"}
UNAVAILABLE_DRIVER_STATUSES = {"unavailable", "on_trip", "off_duty", "leave"}
DEFAULT_REQUIRED_EQUIPMENT = ["oxygen_cylinder", "stretcher", "emergency_kit"]


class TransportService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def dashboard(self, actor: User, filters: dict) -> TransportDashboardRead:
        vehicles = self.list_vehicles(actor, filters)
        drivers = self.list_drivers(actor, filters)
        requests = self.list_requests(actor, filters)
        trips = self.list_trips(actor, filters)
        today = date.today()
        fuel_total = self.db.scalar(select(func.coalesce(func.sum(TransportFuelLog.fuel_cost), 0)).where(TransportFuelLog.fuel_date == today)) or Decimal("0")
        if actor.branch_id:
            fuel_total = self.db.scalar(select(func.coalesce(func.sum(TransportFuelLog.fuel_cost), 0)).where(TransportFuelLog.fuel_date == today, or_(TransportFuelLog.branch_id == actor.branch_id, TransportFuelLog.branch_id.is_(None)))) or Decimal("0")
        by_vehicle_type: dict[str, int] = {}
        by_trip_status: dict[str, int] = {}
        by_priority: dict[str, int] = {}
        for vehicle in vehicles:
            by_vehicle_type[vehicle.vehicle_type] = by_vehicle_type.get(vehicle.vehicle_type, 0) + 1
        for trip in trips:
            by_trip_status[trip.status] = by_trip_status.get(trip.status, 0) + 1
        for request in requests:
            by_priority[request.priority] = by_priority.get(request.priority, 0) + 1
        return TransportDashboardRead(
            total_vehicles=len(vehicles),
            available_ambulances=len([v for v in vehicles if self._is_ambulance(v.vehicle_type) and v.current_status == "available"]),
            available_drivers=len([d for d in drivers if d.availability_status == "available"]),
            active_trips=len([t for t in trips if t.status in ACTIVE_TRIP_STATUSES]),
            pending_requests=len([r for r in requests if r.status in {"requested", "pending_assignment"}]),
            emergency_requests=len([r for r in requests if r.priority in {"emergency", "critical"} or r.urgency == "emergency"]),
            completed_trips_today=len([t for t in trips if t.status == "completed" and t.completed_at and t.completed_at.date() == today]),
            vehicles_under_maintenance=len([v for v in vehicles if v.current_status == "under_maintenance"]),
            fuel_expense_today=fuel_total,
            delayed_trips=len([t for t in trips if t.status == "delayed"]),
            upcoming_scheduled_trips=len([t for t in trips if t.scheduled_at and t.scheduled_at > datetime.now(UTC) and t.status in ACTIVE_TRIP_STATUSES]),
            readiness_alerts=sum(len(v.readiness_alerts or []) for v in vehicles),
            by_vehicle_type=by_vehicle_type,
            by_trip_status=by_trip_status,
            by_priority=by_priority,
        )

    def list_vehicles(self, actor: User, filters: dict | None = None) -> list[TransportVehicle]:
        filters = filters or {}
        stmt = select(TransportVehicle).options(joinedload(TransportVehicle.assigned_driver)).where(TransportVehicle.is_active.is_(True))
        if actor.branch_id:
            stmt = stmt.where(or_(TransportVehicle.branch_id == actor.branch_id, TransportVehicle.branch_id.is_(None)))
        if filters.get("vehicle_type"):
            stmt = stmt.where(TransportVehicle.vehicle_type == filters["vehicle_type"])
        if filters.get("status"):
            stmt = stmt.where(TransportVehicle.current_status == filters["status"])
        return list(self.db.scalars(stmt.order_by(TransportVehicle.vehicle_number.asc())).unique())

    def create_vehicle(self, payload: TransportVehicleCreate, actor: User, context: dict[str, str | None]) -> TransportVehicle:
        self._ensure_unique_vehicle(payload.vehicle_number, payload.registration_number)
        data = payload.model_dump()
        vehicle = TransportVehicle(branch_id=actor.branch_id, **data, created_by=actor.id, updated_by=actor.id)
        vehicle.qr_code = f"transport:vehicle:{payload.vehicle_number}"
        self._refresh_readiness(vehicle)
        self.db.add(vehicle)
        if payload.assigned_driver_id:
            driver = self._get_driver(payload.assigned_driver_id)
            driver.assigned_vehicle = vehicle
        self._audit(actor, "transport.vehicle.create", "transport_vehicle", vehicle, data, context)
        return vehicle

    def update_vehicle(self, vehicle_id: UUID, payload: TransportVehicleCreate, actor: User, context: dict[str, str | None]) -> TransportVehicle:
        vehicle = self._get_vehicle(vehicle_id)
        for key, value in payload.model_dump().items():
            setattr(vehicle, key, value)
        vehicle.updated_by = actor.id
        self._refresh_readiness(vehicle)
        self._audit(actor, "transport.vehicle.update", "transport_vehicle", vehicle, payload.model_dump(mode="json"), context)
        return vehicle

    def list_drivers(self, actor: User, filters: dict | None = None) -> list[TransportDriver]:
        filters = filters or {}
        stmt = select(TransportDriver).options(joinedload(TransportDriver.assigned_vehicle), joinedload(TransportDriver.employee)).where(TransportDriver.is_active.is_(True))
        if actor.branch_id:
            stmt = stmt.where(or_(TransportDriver.branch_id == actor.branch_id, TransportDriver.branch_id.is_(None)))
        if filters.get("driver_id"):
            stmt = stmt.where(TransportDriver.id == filters["driver_id"])
        if filters.get("status"):
            stmt = stmt.where(TransportDriver.availability_status == filters["status"])
        return list(self.db.scalars(stmt.order_by(TransportDriver.driver_name.asc())).unique())

    def create_driver(self, payload: TransportDriverCreate, actor: User, context: dict[str, str | None]) -> TransportDriver:
        if self.db.scalar(select(TransportDriver).where(func.lower(TransportDriver.license_number) == payload.license_number.lower())):
            raise AppException(409, "driver_license_exists", "Driver license already exists")
        data = payload.model_dump()
        if payload.employee_id:
            employee = self.db.get(HREmployee, payload.employee_id)
            if employee and not payload.driver_name:
                data["driver_name"] = employee.full_name
        driver = TransportDriver(branch_id=actor.branch_id, **data, created_by=actor.id, updated_by=actor.id)
        driver.qr_code = f"transport:driver:{payload.license_number}"
        self.db.add(driver)
        if payload.assigned_vehicle_id:
            vehicle = self._get_vehicle(payload.assigned_vehicle_id)
            vehicle.assigned_driver = driver
        self._audit(actor, "transport.driver.create", "transport_driver", driver, data, context)
        return driver

    def update_driver(self, driver_id: UUID, payload: TransportDriverCreate, actor: User, context: dict[str, str | None]) -> TransportDriver:
        driver = self._get_driver(driver_id)
        for key, value in payload.model_dump().items():
            setattr(driver, key, value)
        driver.updated_by = actor.id
        self._audit(actor, "transport.driver.update", "transport_driver", driver, payload.model_dump(mode="json"), context)
        return driver

    def list_requests(self, actor: User, filters: dict | None = None) -> list[TransportRequest]:
        filters = filters or {}
        stmt = self._request_query(actor)
        if filters.get("status"):
            stmt = stmt.where(TransportRequest.status == filters["status"])
        if filters.get("priority"):
            stmt = stmt.where(TransportRequest.priority == filters["priority"])
        if filters.get("trip_type"):
            stmt = stmt.where(TransportRequest.trip_type == filters["trip_type"])
        if filters.get("department"):
            stmt = stmt.where(TransportRequest.source_department == filters["department"])
        if filters.get("date"):
            target = filters["date"]
            if isinstance(target, str):
                target = date.fromisoformat(target)
            start = datetime(target.year, target.month, target.day, tzinfo=UTC)
            stmt = stmt.where(TransportRequest.required_at >= start, TransportRequest.required_at < start + timedelta(days=1))
        return list(self.db.scalars(stmt.order_by((TransportRequest.priority.in_(["emergency", "critical"])).desc(), TransportRequest.required_at.asc())).unique())

    def create_request(self, payload: TransportRequestCreate, actor: User, context: dict[str, str | None], *, quick_emergency: bool = False) -> TransportRequest:
        required_at = payload.required_at or datetime.now(UTC)
        priority = "emergency" if quick_emergency else payload.priority
        urgency = "emergency" if quick_emergency else payload.urgency
        item = TransportRequest(
            branch_id=actor.branch_id,
            request_number=self._next_number("TRQ", TransportRequest.request_number),
            requested_by_user_id=actor.id,
            required_at=required_at,
            status="pending_assignment",
            priority=priority,
            urgency=urgency,
            billing_status="pending" if payload.billing_required else "not_required",
            **payload.model_dump(exclude={"required_at", "priority", "urgency"}),
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.db.add(item)
        self._audit(actor, "transport.request.create", "transport_request", item, payload.model_dump(mode="json"), context)
        return item

    def dispatch(self, request_id: UUID, payload: TransportDispatchRequest, actor: User, context: dict[str, str | None]) -> TransportTrip:
        request = self._get_request(request_id)
        vehicle = self._get_vehicle(payload.vehicle_id)
        driver = self._get_driver(payload.driver_id)
        self._assert_assignable(vehicle, driver, payload.override, payload.override_reason)
        self._assert_not_double_booked(vehicle.id, driver.id, payload.override, payload.override_reason)
        trip = TransportTrip(
            branch_id=actor.branch_id or request.branch_id,
            request=request,
            trip_number=self._next_number("TRP", TransportTrip.trip_number),
            vehicle=vehicle,
            driver=driver,
            patient_id=request.patient_id,
            staff_employee_id=request.staff_employee_id,
            pickup_location=request.pickup_location,
            dropoff_location=request.dropoff_location,
            scheduled_at=payload.scheduled_at or request.required_at,
            trip_type=request.trip_type or request.request_type,
            priority=request.priority,
            status="dispatched" if request.urgency == "emergency" else "vehicle_assigned",
            billing_status=request.billing_status,
            remarks=payload.remarks,
            qr_code=f"transport:trip:{self._next_number('TRP', TransportTrip.trip_number)}",
            created_by=actor.id,
            updated_by=actor.id,
        )
        trip.trip_number = trip.qr_code.removeprefix("transport:trip:")
        self.db.add(trip)
        self.db.flush()
        request.assigned_vehicle = vehicle
        request.assigned_driver = driver
        request.status = trip.status
        request.override_used = payload.override
        request.override_reason = payload.override_reason
        vehicle.current_status = "on_trip" if trip.status == "dispatched" else "assigned"
        driver.availability_status = "on_trip" if trip.status == "dispatched" else "assigned"
        self._audit(actor, "transport.dispatch", "transport_trip", trip, payload.model_dump(mode="json"), context)
        return trip

    def list_trips(self, actor: User, filters: dict | None = None) -> list[TransportTrip]:
        filters = filters or {}
        stmt = (
            select(TransportTrip)
            .options(joinedload(TransportTrip.vehicle), joinedload(TransportTrip.driver), joinedload(TransportTrip.patient), joinedload(TransportTrip.staff_employee), joinedload(TransportTrip.request), joinedload(TransportTrip.completed_by))
            .where(TransportTrip.is_active.is_(True))
        )
        if actor.branch_id:
            stmt = stmt.where(or_(TransportTrip.branch_id == actor.branch_id, TransportTrip.branch_id.is_(None)))
        if filters.get("status"):
            stmt = stmt.where(TransportTrip.status == filters["status"])
        if filters.get("trip_type"):
            stmt = stmt.where(TransportTrip.trip_type == filters["trip_type"])
        if filters.get("driver_id"):
            stmt = stmt.where(TransportTrip.driver_id == filters["driver_id"])
        if filters.get("vehicle_id"):
            stmt = stmt.where(TransportTrip.vehicle_id == filters["vehicle_id"])
        return list(self.db.scalars(stmt.order_by(TransportTrip.created_at.desc())).unique())

    def update_trip_status(self, trip_id: UUID, payload: TransportTripStatusUpdate, actor: User, context: dict[str, str | None]) -> TransportTrip:
        trip = self._get_trip(trip_id)
        now = datetime.now(UTC)
        previous = trip.status
        trip.status = payload.status
        if payload.status in {"dispatched", "in_transit"} and not trip.start_time:
            trip.start_time = payload.start_time or now
        if payload.status == "completed":
            trip.end_time = payload.end_time or now
            trip.completed_at = now
            trip.completed_by_user_id = actor.id
            trip.vehicle.current_status = "available"
            trip.driver.availability_status = "available"
        elif payload.status == "cancelled":
            trip.vehicle.current_status = "available"
            trip.driver.availability_status = "available"
        elif payload.status == "delayed":
            trip.vehicle.current_status = "on_trip"
            trip.driver.availability_status = "on_trip"
        else:
            trip.vehicle.current_status = "on_trip"
            trip.driver.availability_status = "on_trip"
        if trip.request:
            trip.request.status = payload.status
            trip.request.billing_status = payload.billing_status or trip.request.billing_status
        for key in ("distance_km", "waiting_minutes", "charges", "billing_status", "remarks"):
            value = getattr(payload, key)
            if value is not None:
                setattr(trip, key, value)
        trip.updated_by = actor.id
        self._audit(actor, "transport.trip.status", "transport_trip", trip, {"from": previous, "to": payload.status}, context)
        return trip

    def update_location(self, trip_id: UUID, payload: TransportLocationUpdate, actor: User, context: dict[str, str | None]) -> TransportTrip:
        trip = self._get_trip(trip_id)
        recorded_at = payload.recorded_at or datetime.now(UTC)
        update = payload.model_dump(mode="json")
        update["recorded_at"] = recorded_at.isoformat()
        trip.location_updates = [*(trip.location_updates or []), update]
        trip.vehicle.current_latitude = payload.latitude
        trip.vehicle.current_longitude = payload.longitude
        trip.vehicle.location_updated_at = recorded_at
        self._audit(actor, "transport.trip.location", "transport_trip", trip, update, context)
        return trip

    def list_schedules(self, actor: User) -> list[TransportSchedule]:
        stmt = select(TransportSchedule).options(joinedload(TransportSchedule.vehicle), joinedload(TransportSchedule.driver)).where(TransportSchedule.is_active.is_(True))
        if actor.branch_id:
            stmt = stmt.where(or_(TransportSchedule.branch_id == actor.branch_id, TransportSchedule.branch_id.is_(None)))
        return list(self.db.scalars(stmt.order_by(TransportSchedule.start_at.asc())).unique())

    def create_schedule(self, payload: TransportScheduleCreate, actor: User, context: dict[str, str | None]) -> TransportSchedule:
        if payload.vehicle_id or payload.driver_id:
            self._assert_schedule_available(payload.vehicle_id, payload.driver_id, payload.start_at, payload.end_at)
        item = TransportSchedule(branch_id=actor.branch_id, **payload.model_dump(), created_by=actor.id, updated_by=actor.id)
        self.db.add(item)
        self._audit(actor, "transport.schedule.create", "transport_schedule", item, payload.model_dump(mode="json"), context)
        return item

    def list_maintenance(self, actor: User) -> list[TransportMaintenance]:
        stmt = select(TransportMaintenance).options(joinedload(TransportMaintenance.vehicle)).where(TransportMaintenance.is_active.is_(True))
        if actor.branch_id:
            stmt = stmt.where(or_(TransportMaintenance.branch_id == actor.branch_id, TransportMaintenance.branch_id.is_(None)))
        return list(self.db.scalars(stmt.order_by(TransportMaintenance.service_date.desc())).unique())

    def create_maintenance(self, payload: TransportMaintenanceCreate, actor: User, context: dict[str, str | None]) -> TransportMaintenance:
        vehicle = self._get_vehicle(payload.vehicle_id)
        item = TransportMaintenance(branch_id=actor.branch_id or vehicle.branch_id, **payload.model_dump(), created_by=actor.id, updated_by=actor.id)
        if payload.status in {"scheduled", "in_progress"}:
            vehicle.current_status = "under_maintenance"
        self.db.add(item)
        self._audit(actor, "transport.maintenance.create", "transport_maintenance", item, payload.model_dump(mode="json"), context)
        return item

    def list_fuel_logs(self, actor: User) -> list[TransportFuelLog]:
        stmt = select(TransportFuelLog).options(joinedload(TransportFuelLog.vehicle)).where(TransportFuelLog.is_active.is_(True))
        if actor.branch_id:
            stmt = stmt.where(or_(TransportFuelLog.branch_id == actor.branch_id, TransportFuelLog.branch_id.is_(None)))
        return list(self.db.scalars(stmt.order_by(TransportFuelLog.fuel_date.desc())).unique())

    def create_fuel_log(self, payload: TransportFuelLogCreate, actor: User, context: dict[str, str | None]) -> TransportFuelLog:
        vehicle = self._get_vehicle(payload.vehicle_id)
        item = TransportFuelLog(branch_id=actor.branch_id or vehicle.branch_id, **payload.model_dump(), created_by=actor.id, updated_by=actor.id)
        self.db.add(item)
        self._audit(actor, "transport.fuel.create", "transport_fuel_log", item, payload.model_dump(mode="json"), context)
        return item

    def list_settings(self, actor: User) -> list[TransportSetting]:
        stmt = select(TransportSetting).where(TransportSetting.is_active.is_(True))
        if actor.branch_id:
            stmt = stmt.where(or_(TransportSetting.branch_id == actor.branch_id, TransportSetting.branch_id.is_(None)))
        return list(self.db.scalars(stmt.order_by(TransportSetting.setting_key.asc())))

    def upsert_setting(self, payload: TransportSettingCreate, actor: User, context: dict[str, str | None]) -> TransportSetting:
        key = payload.setting_key.strip().lower().replace(" ", "_")
        item = self.db.scalar(select(TransportSetting).where(TransportSetting.setting_key == key, or_(TransportSetting.branch_id == actor.branch_id, TransportSetting.branch_id.is_(None))))
        if not item:
            item = TransportSetting(branch_id=actor.branch_id, setting_key=key, created_by=actor.id)
            self.db.add(item)
        item.setting_value = payload.setting_value
        item.description = payload.description
        item.meta = payload.meta
        item.updated_by = actor.id
        self._audit(actor, "transport.setting.upsert", "transport_setting", item, payload.model_dump(mode="json"), context)
        return item

    def reports(self, actor: User, report_type: str, filters: dict) -> TransportReportRead:
        rows: list[dict] = []
        totals: dict = {}
        if report_type in {"vehicle_list", "ambulance_availability"}:
            vehicles = self.list_vehicles(actor, filters)
            rows = [{"vehicle_number": v.vehicle_number, "type": v.vehicle_type, "status": v.current_status, "readiness": v.readiness_status, "driver": v.assigned_driver.driver_name if v.assigned_driver else None} for v in vehicles]
            totals = {"vehicles": len(rows), "available": len([r for r in rows if r["status"] == "available"])}
        elif report_type in {"driver_availability", "driver_trip"}:
            drivers = self.list_drivers(actor, filters)
            rows = [{"driver": d.driver_name, "contact": d.contact_number, "status": d.availability_status, "license_expiry": d.license_expiry_date.isoformat() if d.license_expiry_date else None} for d in drivers]
            totals = {"drivers": len(rows), "available": len([r for r in rows if r["status"] == "available"])}
        elif report_type in {"fuel_consumption", "vehicle_expense"}:
            logs = self.list_fuel_logs(actor)
            rows = [{"vehicle": l.vehicle.vehicle_number if l.vehicle else None, "date": l.fuel_date.isoformat(), "quantity": float(l.quantity), "cost": float(l.fuel_cost), "category": l.expense_category} for l in logs]
            totals = {"quantity": sum(r["quantity"] for r in rows), "cost": sum(r["cost"] for r in rows)}
        elif report_type == "maintenance":
            logs = self.list_maintenance(actor)
            rows = [{"vehicle": m.vehicle.vehicle_number if m.vehicle else None, "type": m.maintenance_type, "date": m.service_date.isoformat(), "next_service": m.next_service_date.isoformat() if m.next_service_date else None, "cost": float(m.cost), "status": m.status} for m in logs]
            totals = {"records": len(rows), "cost": sum(r["cost"] for r in rows)}
        else:
            trips = self.list_trips(actor, filters)
            rows = [{"trip_number": t.trip_number, "request": t.request.request_number if t.request else None, "vehicle": t.vehicle.vehicle_number if t.vehicle else None, "driver": t.driver.driver_name if t.driver else None, "status": t.status, "trip_type": t.trip_type, "distance_km": float(t.distance_km), "billing_status": t.billing_status} for t in trips]
            totals = {"trips": len(rows), "distance_km": sum(r["distance_km"] for r in rows), "completed": len([r for r in rows if r["status"] == "completed"])}
        return TransportReportRead(report_type=report_type, filters=filters, rows=rows, totals=totals)

    def _request_query(self, actor: User):
        stmt = select(TransportRequest).options(joinedload(TransportRequest.patient), joinedload(TransportRequest.staff_employee), joinedload(TransportRequest.requested_by), joinedload(TransportRequest.assigned_vehicle), joinedload(TransportRequest.assigned_driver)).where(TransportRequest.is_active.is_(True))
        if actor.branch_id:
            stmt = stmt.where(or_(TransportRequest.branch_id == actor.branch_id, TransportRequest.branch_id.is_(None)))
        return stmt

    def _assert_assignable(self, vehicle: TransportVehicle, driver: TransportDriver, override: bool, reason: str | None) -> None:
        problems = []
        if vehicle.current_status in NON_DISPATCHABLE_VEHICLE_STATUSES:
            problems.append(f"Vehicle is {vehicle.current_status}")
        if driver.availability_status in UNAVAILABLE_DRIVER_STATUSES:
            problems.append(f"Driver is {driver.availability_status}")
        if vehicle.readiness_status == "not_ready":
            problems.append("Ambulance readiness failed")
        if problems and not (override and reason):
            raise AppException(409, "transport_assignment_blocked", "; ".join(problems))

    def _assert_not_double_booked(self, vehicle_id: UUID, driver_id: UUID, override: bool, reason: str | None) -> None:
        active = self.db.scalar(select(TransportTrip).where(TransportTrip.status.in_(list(ACTIVE_TRIP_STATUSES)), or_(TransportTrip.vehicle_id == vehicle_id, TransportTrip.driver_id == driver_id)))
        if active and not (override and reason):
            raise AppException(409, "transport_double_booking", "Vehicle or driver already has an active trip")

    def _assert_schedule_available(self, vehicle_id: UUID | None, driver_id: UUID | None, start_at: datetime, end_at: datetime) -> None:
        stmt = select(TransportSchedule).where(TransportSchedule.status.in_(["scheduled", "reserved"]), TransportSchedule.start_at < end_at, TransportSchedule.end_at > start_at)
        if vehicle_id and driver_id:
            stmt = stmt.where(or_(TransportSchedule.vehicle_id == vehicle_id, TransportSchedule.driver_id == driver_id))
        elif vehicle_id:
            stmt = stmt.where(TransportSchedule.vehicle_id == vehicle_id)
        elif driver_id:
            stmt = stmt.where(TransportSchedule.driver_id == driver_id)
        if self.db.scalar(stmt):
            raise AppException(409, "transport_schedule_conflict", "Vehicle or driver is already scheduled")

    def _refresh_readiness(self, vehicle: TransportVehicle) -> None:
        alerts: list[str] = []
        equipment = set(vehicle.equipment_available or [])
        if self._is_ambulance(vehicle.vehicle_type):
            for item in DEFAULT_REQUIRED_EQUIPMENT:
                if item not in equipment:
                    alerts.append(f"Missing {item.replace('_', ' ')}")
        today = date.today()
        for label, expiry in (("insurance", vehicle.insurance_expiry), ("fitness", vehicle.fitness_expiry), ("registration", vehicle.registration_expiry)):
            if expiry and expiry <= today + timedelta(days=30):
                alerts.append(f"{label.title()} expires on {expiry.isoformat()}")
        vehicle.readiness_alerts = alerts
        vehicle.readiness_status = "not_ready" if alerts else "ready"

    def _next_number(self, prefix: str, column) -> str:
        today = date.today().strftime("%Y%m%d")
        count = self.db.scalar(select(func.count()).select_from(column.class_).where(column.ilike(f"{prefix}-{today}-%"))) or 0
        return f"{prefix}-{today}-{int(count) + 1:04d}"

    def _is_ambulance(self, vehicle_type: str | None) -> bool:
        return (vehicle_type or "").lower().replace(" ", "_") in AMBULANCE_TYPES

    def _ensure_unique_vehicle(self, vehicle_number: str, registration_number: str | None) -> None:
        clauses = [func.lower(TransportVehicle.vehicle_number) == vehicle_number.lower()]
        if registration_number:
            clauses.append(func.lower(TransportVehicle.registration_number) == registration_number.lower())
        if self.db.scalar(select(TransportVehicle).where(or_(*clauses))):
            raise AppException(409, "vehicle_exists", "Vehicle number or registration already exists")

    def _get_vehicle(self, vehicle_id: UUID) -> TransportVehicle:
        vehicle = self.db.get(TransportVehicle, vehicle_id)
        if not vehicle:
            raise AppException(404, "vehicle_not_found", "Vehicle not found")
        return vehicle

    def _get_driver(self, driver_id: UUID) -> TransportDriver:
        driver = self.db.get(TransportDriver, driver_id)
        if not driver:
            raise AppException(404, "driver_not_found", "Driver not found")
        return driver

    def _get_request(self, request_id: UUID) -> TransportRequest:
        request = self.db.get(TransportRequest, request_id)
        if not request:
            raise AppException(404, "transport_request_not_found", "Transport request not found")
        return request

    def _get_trip(self, trip_id: UUID) -> TransportTrip:
        trip = self.db.scalar(select(TransportTrip).options(joinedload(TransportTrip.vehicle), joinedload(TransportTrip.driver), joinedload(TransportTrip.request)).where(TransportTrip.id == trip_id))
        if not trip:
            raise AppException(404, "transport_trip_not_found", "Transport trip not found")
        return trip

    def _audit(self, actor: User, action: str, entity_type: str, entity, detail: dict | None, context: dict[str, str | None]) -> None:
        AuditService(self.db).log(actor.id, action, "transport", entity_type, str(getattr(entity, "id", "")), detail or {}, context)
