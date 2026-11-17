"""Add missing weekly slots and profile details for the bundled demo doctors."""
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import inventory  # noqa: F401 -- register catering/inventory relationships
from app.models.encounter import DoctorOPDSchedule
from app.models.user import User


PROFILES = {
    "dr_rahman": ("General Medicine", "MBBS", "Demo OPD room 101"),
    "surgeon_arif": ("General Surgery", "MBBS, FCPS (Surgery)", "Demo OPD room 102"),
    "anesthetist_faria": ("Anesthesiology", "MBBS, MD (Anesthesiology)", "Demo OPD room 103"),
    "ref_dr_sadia": ("General Medicine", "MBBS", "Demo OPD room 104"),
}


def main() -> None:
    with SessionLocal() as db:
        added = 0
        for username, (specialty, degrees, chamber) in PROFILES.items():
            doctor = db.scalar(select(User).where(User.username == username, User.email.like("%@hms.local")))
            if not doctor or not any(role.is_doctor_role for role in doctor.roles):
                continue
            for field, value in {
                "opd_prescription_header_specialty": specialty,
                "opd_prescription_header_degrees": degrees,
                "opd_prescription_header_chamber": chamber,
                "opd_prescription_header_workplace": "HMS demonstration hospital",
            }.items():
                if not getattr(doctor, field):
                    setattr(doctor, field, value)
            for weekday in range(7):
                existing = db.scalar(select(DoctorOPDSchedule.id).where(
                    DoctorOPDSchedule.doctor_user_id == doctor.id,
                    DoctorOPDSchedule.weekday == weekday,
                ))
                if existing:
                    continue
                # The current appointments service stores schedule hours in UTC.
                # 03:00-14:00 UTC is 09:00-20:00 in Bangladesh.
                db.add(DoctorOPDSchedule(
                    doctor_user_id=doctor.id, branch_id=doctor.branch_id, weekday=weekday,
                    start_time="03:00", end_time="14:00", slot_duration_minutes=15,
                    buffer_minutes=0, created_by=doctor.id, updated_by=doctor.id,
                ))
                added += 1
        db.commit()
        print(f"Demo doctor schedules ready: {added} missing days added; existing schedules preserved.")


if __name__ == "__main__":
    main()
