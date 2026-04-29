from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.branch import Branch
from app.models.ot import (
    AnesthesiaRecord,
    OTBillingItem,
    OTBooking,
    OTConsumableUsage,
    OTDocument,
    OTEquipmentUsage,
    OTRoom,
    PostOpRecovery,
    PreOpChecklist,
    SurgeryNote,
    SurgerySchedule,
    SurgeryTeamAssignment,
)
from app.models.patient import Patient
from app.models.user import User


def main() -> None:
    db = SessionLocal()
    try:
        branch = db.scalars(select(Branch).order_by(Branch.created_at)).first()
        actor = db.scalars(select(User).order_by(User.created_at)).first()
        patients = db.scalars(select(Patient).order_by(Patient.created_at).limit(4)).all()
        users = db.scalars(select(User).order_by(User.created_at).limit(8)).all()
        if not branch or not actor or not patients:
            print("OT demo seed skipped: branch, actor, or patients missing.")
            return
        rooms = _rooms(db, branch, actor)
        schedules = _cases(db, branch, actor, patients, users, rooms)
        db.commit()
        print(f"OT demo seed completed: {len(rooms)} rooms, {len(schedules)} surgery schedules.")
    finally:
        db.close()


def _rooms(db, branch: Branch, actor: User) -> list[OTRoom]:
    data = [
        ("OT-1", "Major OT 1", "major", "available", "Level 3", "Laminar airflow, anesthesia workstation, C-arm ready", "4500"),
        ("OT-2", "Emergency OT", "emergency", "booked", "Level 3", "Emergency trauma setup, crash cart, suction", "5500"),
        ("OT-3", "Minor Procedure OT", "minor", "available", "Level 2", "Day-care procedure setup", "2500"),
    ]
    rooms = []
    for room_number, name, room_type, status, floor, equipment, charge in data:
        room = db.scalar(select(OTRoom).where(OTRoom.branch_id == branch.id, OTRoom.room_number == room_number))
        if not room:
            room = OTRoom(branch_id=branch.id, room_number=room_number, name=name, room_type=room_type, status=status, floor=floor, equipment_summary=equipment, hourly_charge=Decimal(charge), created_by=actor.id, updated_by=actor.id)
            db.add(room)
            db.flush()
        rooms.append(room)
    return rooms


def _cases(db, branch: Branch, actor: User, patients: list[Patient], users: list[User], rooms: list[OTRoom]) -> list[SurgerySchedule]:
    now = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    cases = [
        (patients[0], rooms[0], "Laparoscopic Cholecystectomy", "elective", "normal", now + timedelta(hours=2), 90, "Surgery", "Chronic calculous cholecystitis", "scheduled"),
        (patients[min(1, len(patients) - 1)], rooms[1], "Emergency Appendectomy", "emergency", "critical", now + timedelta(hours=1), 75, "Emergency", "Acute appendicitis", "ready_for_ot"),
        (patients[min(2, len(patients) - 1)], rooms[2], "Wound Debridement", "minor", "high", now - timedelta(hours=2), 45, "Surgery", "Infected wound", "completed"),
    ]
    schedules: list[SurgerySchedule] = []
    for index, (patient, room, procedure, surgery_type, priority, start, duration, dept, diagnosis, status) in enumerate(cases):
        booking = db.scalar(select(OTBooking).where(OTBooking.branch_id == branch.id, OTBooking.procedure_name == procedure, OTBooking.patient_id == patient.id))
        if not booking:
            booking = OTBooking(
                branch_id=branch.id,
                patient_id=patient.id,
                source_module="demo",
                booking_number=f"OTB-DEMO-{index + 1:03d}",
                procedure_name=procedure,
                surgery_type=surgery_type,
                priority_level=priority,
                preferred_start_at=start,
                estimated_duration_minutes=duration,
                department_name=dept,
                diagnosis=diagnosis,
                requested_by_user_id=actor.id,
                status=status,
                created_by=actor.id,
                updated_by=actor.id,
            )
            db.add(booking)
            db.flush()
        schedule = db.scalar(select(SurgerySchedule).where(SurgerySchedule.booking_id == booking.id))
        if not schedule:
            schedule = SurgerySchedule(
                branch_id=branch.id,
                booking_id=booking.id,
                room_id=room.id,
                scheduled_start_at=start,
                scheduled_end_at=start + timedelta(minutes=duration),
                primary_surgeon_user_id=users[1].id if len(users) > 1 else actor.id,
                anesthetist_user_id=users[2].id if len(users) > 2 else actor.id,
                scrub_nurse_user_id=users[3].id if len(users) > 3 else actor.id,
                technician_user_id=users[4].id if len(users) > 4 else actor.id,
                status=status,
                surgery_start_at=start if status == "completed" else None,
                surgery_end_at=start + timedelta(minutes=duration) if status == "completed" else None,
                created_by=actor.id,
                updated_by=actor.id,
            )
            db.add(schedule)
            db.flush()
            db.add(PreOpChecklist(schedule_id=schedule.id, consent_signed=True, anesthesia_cleared=status != "scheduled", lab_verified=True, radiology_verified=True, blood_arranged=surgery_type == "emergency", npo_confirmed=True, site_marked=True, equipment_confirmed=True, implant_confirmed=True, allergy_info="No known allergy", pre_op_diagnosis=diagnosis, ready_for_ot=status in {"ready_for_ot", "completed"}, checked_by_user_id=actor.id, created_by=actor.id, updated_by=actor.id))
            db.add(AnesthesiaRecord(schedule_id=schedule.id, anesthesia_type="general" if surgery_type != "minor" else "local", pre_assessment="ASA II, airway reviewed", notes="Standard monitoring planned", clearance_status="cleared" if status != "scheduled" else "pending", signed_off_by_user_id=actor.id if status != "scheduled" else None, signed_off_at=now if status != "scheduled" else None, created_by=actor.id, updated_by=actor.id))
            db.add(SurgeryNote(schedule_id=schedule.id, procedure_performed=procedure if status == "completed" else None, operative_findings="Findings documented for demo case" if status == "completed" else None, surgeon_notes="Procedure tolerated well" if status == "completed" else None, nursing_notes="Counts complete" if status == "completed" else None, instrument_count_confirmed=status == "completed", sponge_count_confirmed=status == "completed", surgery_outcome="successful", created_by=actor.id, updated_by=actor.id))
            db.add(PostOpRecovery(schedule_id=schedule.id, transfer_to="ward" if status == "completed" else "recovery", recovery_admission_at=start + timedelta(minutes=duration + 10) if status == "completed" else None, vitals_summary="Stable", pain_score=2 if status == "completed" else None, consciousness_status="Awake", handover_notes="Ward handover complete" if status == "completed" else None, created_by=actor.id, updated_by=actor.id))
            db.add(SurgeryTeamAssignment(schedule_id=schedule.id, user_id=users[1].id if len(users) > 1 else actor.id, role="primary_surgeon", response_status="confirmed", confirmed_at=now, created_by=actor.id, updated_by=actor.id))
            db.add(OTConsumableUsage(schedule_id=schedule.id, item_name="Surgical drape set", batch_no="OT-B-001", quantity_used=Decimal("1"), unit_cost=Decimal("650"), charged_amount=Decimal("900"), created_by=actor.id, updated_by=actor.id))
            db.add(OTEquipmentUsage(schedule_id=schedule.id, equipment_name="Anesthesia workstation", usage_notes="Checked and ready", charge_amount=Decimal("1200"), confirmed=True, created_by=actor.id, updated_by=actor.id))
            db.add(OTBillingItem(schedule_id=schedule.id, charge_type="procedure", description=procedure, amount=Decimal("25000") if surgery_type != "minor" else Decimal("8000"), payment_status="pending", created_by=actor.id, updated_by=actor.id))
            db.add(OTDocument(schedule_id=schedule.id, document_type="consent", title=f"Consent - {procedure}", body="Digital consent template generated for demo.", created_by=actor.id, updated_by=actor.id))
        schedules.append(schedule)
    return schedules


if __name__ == "__main__":
    main()
