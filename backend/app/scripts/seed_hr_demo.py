from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.branch import Branch
from app.models.department import Department
from app.models.hr import (
    HRAttendance,
    HRCandidate,
    HRDesignation,
    HRDutyRoster,
    HREmployee,
    HREmployeeLoan,
    HRLeaveRequest,
    HRLeaveType,
    HROvertimeRequest,
    HRPerformanceReview,
    HRRecruitmentJob,
    HRSalaryStructure,
    HRSetting,
    HRShift,
)
from app.models.user import User
from app.modules.hr.service import HRService
from app.schemas.hr import HRPayrollRunCreate


DEPARTMENTS = [
    ("HR", "Human Resources"),
    ("NURSING", "Nursing"),
    ("LAB", "Laboratory"),
    ("RAD", "Radiology"),
    ("PHARM", "Pharmacy"),
    ("ACC", "Accounts"),
    ("ADMIN", "Administration"),
    ("ICU", "ICU"),
]

EMPLOYEES = [
    ("HR-1001", "Ayesha Rahman", "female", "hr_manager", "HR", "HR Manager", "admin_staff", "01710002001", "ayesha.hr@hms.local", "85000"),
    ("HR-1002", "Dr. Farhan Karim", "male", "full_time", "ADMIN", "Consultant Physician", "doctor", "01710002002", "farhan.karim@hms.local", "180000"),
    ("HR-1003", "Nusrat Jahan", "female", "full_time", "NURSING", "Senior Staff Nurse", "nurse", "01710002003", "nusrat.nurse@hms.local", "62000"),
    ("HR-1004", "Tariq Hasan", "male", "full_time", "LAB", "Lab Technologist", "lab_technician", "01710002004", "tariq.lab@hms.local", "58000"),
    ("HR-1005", "Mim Akter", "female", "full_time", "RAD", "Radiology Technician", "lab_technician", "01710002005", "mim.rad@hms.local", "60000"),
    ("HR-1006", "Shuvo Das", "male", "full_time", "PHARM", "Pharmacist", "pharmacist", "01710002006", "shuvo.pharm@hms.local", "55000"),
    ("HR-1007", "Rima Sultana", "female", "full_time", "ACC", "Payroll Officer", "accountant", "01710002007", "rima.accounts@hms.local", "70000"),
    ("HR-1008", "Kamal Hossain", "male", "contract", "ADMIN", "Security Supervisor", "security", "01710002008", "kamal.security@hms.local", "30000"),
    ("HR-1009", "Parvin Begum", "female", "contract", "ADMIN", "Cleaner", "cleaner", "01710002009", "parvin.clean@hms.local", "24000"),
]


def main() -> None:
    db = SessionLocal()
    try:
        branch = db.scalars(select(Branch).order_by(Branch.created_at)).first()
        actor = db.scalars(select(User).order_by(User.created_at)).first()
        if not branch or not actor:
            print("HR demo seed skipped: branch or user not found.")
            return

        departments = _ensure_departments(db, branch, actor)
        designations = _ensure_designations(db, branch, actor, departments)
        employees = _ensure_employees(db, branch, actor, departments, designations)
        shifts = _ensure_shifts(db, branch, actor)
        leave_types = _ensure_leave_types(db, branch, actor)
        _ensure_settings(db, branch, actor)
        _ensure_salary_structures(db, branch, actor, employees)
        _ensure_attendance(db, branch, actor, employees)
        _ensure_roster(db, branch, actor, employees, shifts)
        _ensure_leave_requests(db, branch, actor, employees, leave_types)
        _ensure_overtime_and_loans(db, branch, actor, employees)
        _ensure_recruitment_and_performance(db, branch, actor, departments, employees)
        db.commit()

        try:
            HRService(db).process_payroll(HRPayrollRunCreate(payroll_month=date.today().strftime("%Y-%m"), note="Seeded monthly payroll preview"), actor)
        except Exception:
            db.rollback()

        print(f"HR demo seed completed: {len(employees)} employees, {len(shifts)} shifts, {len(leave_types)} leave types.")
    finally:
        db.close()


def _ensure_departments(db, branch: Branch, actor: User) -> dict[str, Department]:
    existing = {item.code: item for item in db.scalars(select(Department).where(Department.branch_id == branch.id))}
    for code, name in DEPARTMENTS:
        if code not in existing:
            department = Department(branch_id=branch.id, code=code, name=name, description=f"{name} department", created_by=actor.id, updated_by=actor.id)
            db.add(department)
            db.flush()
            existing[code] = department
    return existing


def _ensure_designations(db, branch: Branch, actor: User, departments: dict[str, Department]) -> dict[str, HRDesignation]:
    rows = {
        "HR Manager": "HR",
        "Consultant Physician": "ADMIN",
        "Senior Staff Nurse": "NURSING",
        "Lab Technologist": "LAB",
        "Radiology Technician": "RAD",
        "Pharmacist": "PHARM",
        "Payroll Officer": "ACC",
        "Security Supervisor": "ADMIN",
        "Cleaner": "ADMIN",
    }
    existing = {item.name: item for item in db.scalars(select(HRDesignation).where(HRDesignation.branch_id == branch.id))}
    for name, department_code in rows.items():
        if name not in existing:
            item = HRDesignation(branch_id=branch.id, department_id=departments[department_code].id, name=name, code=name.upper().replace(" ", "_"), grade="G1", created_by=actor.id, updated_by=actor.id)
            db.add(item)
            db.flush()
            existing[name] = item
    return existing


def _ensure_employees(db, branch: Branch, actor: User, departments: dict[str, Department], designations: dict[str, HRDesignation]) -> list[HREmployee]:
    employees: list[HREmployee] = []
    for index, (staff_code, name, gender, emp_type, dept_code, designation, category, phone, email, _) in enumerate(EMPLOYEES):
        employee = db.scalar(select(HREmployee).where(HREmployee.staff_code == staff_code))
        if not employee:
            employee = HREmployee(
                branch_id=branch.id,
                staff_code=staff_code,
                full_name=name,
                gender=gender,
                phone=phone,
                email=email,
                department_id=departments[dept_code].id,
                designation_id=designations[designation].id,
                employee_type=emp_type,
                employee_category=category,
                joining_date=date.today() - timedelta(days=45 + index * 18),
                employment_status="active",
                qualification="Relevant professional qualification and hospital workflow training",
                specialization=designation,
                license_number=f"LIC-{staff_code}" if category in {"doctor", "nurse", "lab_technician", "pharmacist"} else None,
                license_expiry_date=date.today() + timedelta(days=30 + index * 12) if category in {"doctor", "nurse", "lab_technician", "pharmacist"} else None,
                emergency_contact_name="Family Contact",
                emergency_contact_phone=f"01810002{index:03d}",
                bank_name="Demo Bank PLC",
                bank_account_name=name,
                bank_account_number=f"12004500{index:04d}",
                tax_id=f"TIN-{staff_code}",
                created_by=actor.id,
                updated_by=actor.id,
            )
            db.add(employee)
            db.flush()
        employees.append(employee)
    return employees


def _ensure_shifts(db, branch: Branch, actor: User) -> list[HRShift]:
    rows = [
        ("Morning", "MORN", "morning", "08:00", "14:00", "0"),
        ("Evening", "EVE", "evening", "14:00", "20:00", "0"),
        ("Night", "NGT", "night", "20:00", "08:00", "700"),
        ("Emergency Duty", "EMR", "emergency", "08:00", "20:00", "1000"),
        ("On-call Duty", "ONC", "on_call", "20:00", "08:00", "1200"),
    ]
    shifts = []
    for name, code, shift_type, start, end, allowance in rows:
        shift = db.scalar(select(HRShift).where(HRShift.branch_id == branch.id, HRShift.code == code))
        if not shift:
            shift = HRShift(branch_id=branch.id, name=name, code=code, shift_type=shift_type, start_time=start, end_time=end, break_minutes=30, allowance_amount=Decimal(allowance), created_by=actor.id, updated_by=actor.id)
            db.add(shift)
            db.flush()
        shifts.append(shift)
    return shifts


def _ensure_leave_types(db, branch: Branch, actor: User) -> list[HRLeaveType]:
    rows = [("Casual Leave", "CL", "10", True), ("Sick Leave", "SL", "14", True), ("Annual Leave", "AL", "18", True), ("Maternity Leave", "ML", "112", True), ("Emergency Leave", "EL", "5", True), ("Unpaid Leave", "UL", "0", False), ("Study Leave", "STL", "7", True)]
    items = []
    for name, code, quota, paid in rows:
        item = db.scalar(select(HRLeaveType).where(HRLeaveType.branch_id == branch.id, HRLeaveType.code == code))
        if not item:
            item = HRLeaveType(branch_id=branch.id, name=name, code=code, annual_quota=Decimal(quota), is_paid=paid, requires_approval=True, created_by=actor.id, updated_by=actor.id)
            db.add(item)
            db.flush()
        items.append(item)
    return items


def _ensure_settings(db, branch: Branch, actor: User) -> None:
    settings = {
        "staff_code_prefix": "HR",
        "monthly_working_days": "26",
        "late_deduction_enabled": "true",
        "license_expiry_alert_days": "45",
        "contract_expiry_alert_days": "45",
        "payroll_requires_approval": "true",
        "mobile_attendance_geo_required": "false",
        "bank_transfer_export_format": "standard_bank_csv",
        "minimum_nurse_per_shift": "3",
    }
    for key, value in settings.items():
        if not db.scalar(select(HRSetting).where(HRSetting.branch_id == branch.id, HRSetting.setting_key == key)):
            db.add(HRSetting(branch_id=branch.id, setting_key=key, setting_value=value, description=f"HR configurable setting: {key}", created_by=actor.id, updated_by=actor.id))


def _ensure_salary_structures(db, branch: Branch, actor: User, employees: list[HREmployee]) -> None:
    salary_map = {row[0]: Decimal(row[-1]) for row in EMPLOYEES}
    for employee in employees:
        if not db.scalar(select(HRSalaryStructure).where(HRSalaryStructure.employee_id == employee.id)):
            basic = salary_map[employee.staff_code]
            db.add(
                HRSalaryStructure(
                    branch_id=branch.id,
                    employee_id=employee.id,
                    effective_from=employee.joining_date,
                    basic_salary=basic,
                    house_rent_allowance=basic * Decimal("0.35"),
                    medical_allowance=Decimal("3000"),
                    transport_allowance=Decimal("2500"),
                    food_allowance=Decimal("1800"),
                    night_duty_allowance=Decimal("1000") if employee.employee_category in {"nurse", "lab_technician", "security"} else Decimal("0"),
                    on_call_allowance=Decimal("1500") if employee.employee_category == "doctor" else Decimal("0"),
                    emergency_duty_allowance=Decimal("1000") if employee.employee_category in {"doctor", "nurse"} else Decimal("0"),
                    overtime_hourly_rate=(basic / Decimal("208")).quantize(Decimal("0.01")),
                    tax_deduction=basic * Decimal("0.03") if basic >= Decimal("70000") else Decimal("0"),
                    provident_fund_deduction=basic * Decimal("0.05"),
                    created_by=actor.id,
                    updated_by=actor.id,
                )
            )


def _ensure_attendance(db, branch: Branch, actor: User, employees: list[HREmployee]) -> None:
    statuses = ["present", "present", "late", "present", "on_leave", "present", "half_day", "absent", "present"]
    for employee, status in zip(employees, statuses, strict=False):
        if not db.scalar(select(HRAttendance).where(HRAttendance.employee_id == employee.id, HRAttendance.attendance_date == date.today())):
            db.add(HRAttendance(branch_id=branch.id, employee_id=employee.id, attendance_date=date.today(), status=status, check_in_at=datetime.now(UTC), working_hours=Decimal("4") if status == "half_day" else Decimal("8"), late_minutes=25 if status == "late" else 0, created_by=actor.id, updated_by=actor.id))


def _ensure_roster(db, branch: Branch, actor: User, employees: list[HREmployee], shifts: list[HRShift]) -> None:
    for index, employee in enumerate(employees):
        shift = shifts[index % len(shifts)]
        if not db.scalar(select(HRDutyRoster).where(HRDutyRoster.employee_id == employee.id, HRDutyRoster.roster_date == date.today(), HRDutyRoster.shift_id == shift.id)):
            db.add(HRDutyRoster(branch_id=branch.id, employee_id=employee.id, shift_id=shift.id, roster_date=date.today(), duty_area=["OPD", "Ward", "ICU", "Lab", "Radiology"][index % 5], duty_type=shift.shift_type, created_by=actor.id, updated_by=actor.id))


def _ensure_leave_requests(db, branch: Branch, actor: User, employees: list[HREmployee], leave_types: list[HRLeaveType]) -> None:
    leave_type = leave_types[0]
    employee = employees[2]
    if not db.scalar(select(HRLeaveRequest).where(HRLeaveRequest.employee_id == employee.id, HRLeaveRequest.start_date == date.today() + timedelta(days=3))):
        db.add(HRLeaveRequest(branch_id=branch.id, employee_id=employee.id, leave_type_id=leave_type.id, start_date=date.today() + timedelta(days=3), end_date=date.today() + timedelta(days=4), number_of_days=Decimal("2"), reason="Family program", status="pending", created_by=actor.id, updated_by=actor.id))


def _ensure_overtime_and_loans(db, branch: Branch, actor: User, employees: list[HREmployee]) -> None:
    employee = employees[1]
    if not db.scalar(select(HROvertimeRequest).where(HROvertimeRequest.employee_id == employee.id, HROvertimeRequest.overtime_date == date.today())):
        db.add(HROvertimeRequest(branch_id=branch.id, employee_id=employee.id, overtime_date=date.today(), overtime_hours=Decimal("3"), overtime_type="emergency", status="approved", reason="Emergency duty coverage", approved_by_user_id=actor.id, created_by=actor.id, updated_by=actor.id))
    loan_employee = employees[6]
    if not db.scalar(select(HREmployeeLoan).where(HREmployeeLoan.employee_id == loan_employee.id)):
        db.add(HREmployeeLoan(branch_id=branch.id, employee_id=loan_employee.id, loan_type="advance", approved_amount=Decimal("50000"), monthly_installment=Decimal("5000"), deduction_start_month=date.today().strftime("%Y-%m"), remaining_balance=Decimal("50000"), status="active", note="Festival advance", created_by=actor.id, updated_by=actor.id))


def _ensure_recruitment_and_performance(db, branch: Branch, actor: User, departments: dict[str, Department], employees: list[HREmployee]) -> None:
    if not db.scalar(select(HRRecruitmentJob).where(HRRecruitmentJob.branch_id == branch.id, HRRecruitmentJob.title == "ICU Staff Nurse")):
        job = HRRecruitmentJob(branch_id=branch.id, department_id=departments["ICU"].id, title="ICU Staff Nurse", number_of_positions=4, status="open", closing_date=date.today() + timedelta(days=21), salary_range="BDT 45,000 - 65,000", description="ICU nursing roster expansion", created_by=actor.id, updated_by=actor.id)
        db.add(job)
        db.flush()
        db.add(HRCandidate(job_id=job.id, full_name="Sadia Islam", phone="01710003001", email="sadia.candidate@hms.local", status="shortlisted", interview_at=datetime.now(UTC) + timedelta(days=2), notes="Five years ICU experience", created_by=actor.id, updated_by=actor.id))
    employee = employees[0]
    if not db.scalar(select(HRPerformanceReview).where(HRPerformanceReview.employee_id == employee.id, HRPerformanceReview.review_period == date.today().strftime("%Y-%m"))):
        db.add(HRPerformanceReview(employee_id=employee.id, review_period=date.today().strftime("%Y-%m"), rating=Decimal("4.5"), feedback="Strong HR operations ownership.", kpi_summary="Recruitment SLA, attendance hygiene, payroll closure", recommendation="Eligible for annual increment", created_by=actor.id, updated_by=actor.id))


if __name__ == "__main__":
    main()
