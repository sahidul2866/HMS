from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import and_, desc, func, or_
from sqlalchemy.orm import Session

from app.models.hr import (
    Attendance,
    Candidate,
    Department,
    Designation,
    DutyRoster,
    Employee,
    EmployeeDeduction,
    EmployeeDocument,
    EmployeeLoan,
    LeaveBalance,
    LeaveRequest,
    LeaveType,
    OvertimeRequest,
    Payslip,
    PayrollRun,
    PerformanceReview,
    RecruitmentJob,
    Resignation,
    SalaryStructure,
    Shift,
)


class DepartmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, branch_id: UUID, skip: int = 0, limit: int = 10):
        query = self.db.query(Department).filter(Department.branch_id == branch_id, Department.is_active == True)
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return items, total

    def get_by_id(self, department_id: UUID, branch_id: UUID):
        return (
            self.db.query(Department)
            .filter(Department.id == department_id, Department.branch_id == branch_id)
            .first()
        )

    def get_by_name(self, name: str, branch_id: UUID):
        return (
            self.db.query(Department)
            .filter(
                Department.name.ilike(f"%{name}%"),
                Department.branch_id == branch_id,
                Department.is_active == True,
            )
            .all()
        )

    def create(self, data: dict):
        department = Department(**data)
        self.db.add(department)
        self.db.flush()
        return department

    def update(self, department_id: UUID, data: dict, branch_id: UUID):
        department = self.get_by_id(department_id, branch_id)
        if department:
            for key, value in data.items():
                if value is not None:
                    setattr(department, key, value)
        return department

    def deactivate(self, department_id: UUID, branch_id: UUID):
        department = self.get_by_id(department_id, branch_id)
        if department:
            department.is_active = False
        return department


class DesignationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, branch_id: UUID, skip: int = 0, limit: int = 10):
        query = self.db.query(Designation).filter(Designation.branch_id == branch_id, Designation.is_active == True)
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return items, total

    def get_by_id(self, designation_id: UUID, branch_id: UUID):
        return (
            self.db.query(Designation)
            .filter(Designation.id == designation_id, Designation.branch_id == branch_id)
            .first()
        )

    def get_by_department(self, department_id: UUID, branch_id: UUID):
        return (
            self.db.query(Designation)
            .filter(
                Designation.department_id == department_id,
                Designation.branch_id == branch_id,
                Designation.is_active == True,
            )
            .all()
        )

    def create(self, data: dict):
        designation = Designation(**data)
        self.db.add(designation)
        self.db.flush()
        return designation

    def update(self, designation_id: UUID, data: dict, branch_id: UUID):
        designation = self.get_by_id(designation_id, branch_id)
        if designation:
            for key, value in data.items():
                if value is not None:
                    setattr(designation, key, value)
        return designation


class EmployeeRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, branch_id: UUID, skip: int = 0, limit: int = 10, search: str | None = None):
        query = self.db.query(Employee).filter(Employee.branch_id == branch_id)
        if search:
            query = query.filter(
                or_(
                    Employee.employee_id.ilike(f"%{search}%"),
                    Employee.first_name.ilike(f"%{search}%"),
                    Employee.last_name.ilike(f"%{search}%"),
                    Employee.email.ilike(f"%{search}%"),
                )
            )
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return items, total

    def get_by_id(self, employee_id: UUID, branch_id: UUID):
        return self.db.query(Employee).filter(Employee.id == employee_id, Employee.branch_id == branch_id).first()

    def get_by_employee_id(self, employee_id: str, branch_id: UUID):
        return self.db.query(Employee).filter(Employee.employee_id == employee_id, Employee.branch_id == branch_id).first()

    def get_by_department(self, department_id: UUID, branch_id: UUID):
        return (
            self.db.query(Employee)
            .filter(Employee.department_id == department_id, Employee.branch_id == branch_id, Employee.is_active == True)
            .all()
        )

    def get_by_category(self, category: str, branch_id: UUID):
        return (
            self.db.query(Employee)
            .filter(Employee.employee_category == category, Employee.branch_id == branch_id, Employee.is_active == True)
            .all()
        )

    def get_by_status(self, status: str, branch_id: UUID):
        return (
            self.db.query(Employee)
            .filter(Employee.employment_status == status, Employee.branch_id == branch_id, Employee.is_active == True)
            .all()
        )

    def create(self, data: dict):
        employee = Employee(**data)
        self.db.add(employee)
        self.db.flush()
        return employee

    def update(self, employee_id: UUID, data: dict, branch_id: UUID):
        employee = self.get_by_id(employee_id, branch_id)
        if employee:
            for key, value in data.items():
                if value is not None:
                    setattr(employee, key, value)
        return employee

    def deactivate(self, employee_id: UUID, branch_id: UUID):
        employee = self.get_by_id(employee_id, branch_id)
        if employee:
            employee.is_active = False
        return employee


class EmployeeDocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_employee(self, employee_id: UUID, branch_id: UUID):
        return (
            self.db.query(EmployeeDocument)
            .filter(EmployeeDocument.employee_id == employee_id, EmployeeDocument.branch_id == branch_id)
            .all()
        )

    def create(self, data: dict):
        document = EmployeeDocument(**data)
        self.db.add(document)
        self.db.flush()
        return document


class AttendanceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_employee_date(self, employee_id: UUID, attendance_date: date, branch_id: UUID):
        return (
            self.db.query(Attendance)
            .filter(
                Attendance.employee_id == employee_id,
                Attendance.attendance_date == attendance_date,
                Attendance.branch_id == branch_id,
            )
            .first()
        )

    def get_by_employee_daterange(self, employee_id: UUID, start_date: date, end_date: date, branch_id: UUID):
        return (
            self.db.query(Attendance)
            .filter(
                Attendance.employee_id == employee_id,
                Attendance.attendance_date >= start_date,
                Attendance.attendance_date <= end_date,
                Attendance.branch_id == branch_id,
            )
            .all()
        )

    def get_by_date(self, attendance_date: date, branch_id: UUID, skip: int = 0, limit: int = 100):
        query = self.db.query(Attendance).filter(
            Attendance.attendance_date == attendance_date, Attendance.branch_id == branch_id
        )
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return items, total

    def create(self, data: dict):
        attendance = Attendance(**data)
        self.db.add(attendance)
        self.db.flush()
        return attendance

    def update(self, attendance_id: UUID, data: dict, branch_id: UUID):
        attendance = self.db.query(Attendance).filter(Attendance.id == attendance_id, Attendance.branch_id == branch_id).first()
        if attendance:
            for key, value in data.items():
                if value is not None:
                    setattr(attendance, key, value)
        return attendance

    def get_summary(self, employee_id: UUID, start_date: date, end_date: date, branch_id: UUID):
        records = self.get_by_employee_daterange(employee_id, start_date, end_date, branch_id)
        total_days = (end_date - start_date).days + 1
        present_days = sum(1 for r in records if r.status == "present")
        absent_days = sum(1 for r in records if r.status == "absent")
        late_days = sum(1 for r in records if r.status == "late")
        half_days = sum(1 for r in records if r.status == "half_day")
        on_leave_days = sum(1 for r in records if r.status == "on_leave")

        return {
            "total_days": total_days,
            "present_days": present_days,
            "absent_days": absent_days,
            "late_days": late_days,
            "half_days": half_days,
            "on_leave_days": on_leave_days,
            "attendance_percentage": Decimal(present_days / total_days * 100) if total_days > 0 else Decimal(0),
        }


class ShiftRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, branch_id: UUID, skip: int = 0, limit: int = 10):
        query = self.db.query(Shift).filter(Shift.branch_id == branch_id, Shift.is_active == True)
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return items, total

    def get_by_id(self, shift_id: UUID, branch_id: UUID):
        return self.db.query(Shift).filter(Shift.id == shift_id, Shift.branch_id == branch_id).first()

    def create(self, data: dict):
        shift = Shift(**data)
        self.db.add(shift)
        self.db.flush()
        return shift


class DutyRosterRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_employee_date(self, employee_id: UUID, roster_date: date, branch_id: UUID):
        return (
            self.db.query(DutyRoster)
            .filter(
                DutyRoster.employee_id == employee_id,
                DutyRoster.roster_date == roster_date,
                DutyRoster.branch_id == branch_id,
            )
            .first()
        )

    def get_by_daterange(self, start_date: date, end_date: date, branch_id: UUID, skip: int = 0, limit: int = 100):
        query = self.db.query(DutyRoster).filter(
            DutyRoster.roster_date >= start_date, DutyRoster.roster_date <= end_date, DutyRoster.branch_id == branch_id
        )
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return items, total

    def get_by_employee(self, employee_id: UUID, branch_id: UUID, skip: int = 0, limit: int = 10):
        query = self.db.query(DutyRoster).filter(DutyRoster.employee_id == employee_id, DutyRoster.branch_id == branch_id)
        total = query.count()
        items = query.offset(skip).limit(limit).order_by(desc(DutyRoster.roster_date)).all()
        return items, total

    def create(self, data: dict):
        roster = DutyRoster(**data)
        self.db.add(roster)
        self.db.flush()
        return roster


class LeaveTypeRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, branch_id: UUID, skip: int = 0, limit: int = 10):
        query = self.db.query(LeaveType).filter(LeaveType.branch_id == branch_id, LeaveType.is_active == True)
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return items, total

    def get_by_id(self, leave_type_id: UUID, branch_id: UUID):
        return self.db.query(LeaveType).filter(LeaveType.id == leave_type_id, LeaveType.branch_id == branch_id).first()

    def create(self, data: dict):
        leave_type = LeaveType(**data)
        self.db.add(leave_type)
        self.db.flush()
        return leave_type


class LeaveRequestRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_employee(self, employee_id: UUID, branch_id: UUID, skip: int = 0, limit: int = 10):
        query = self.db.query(LeaveRequest).filter(LeaveRequest.employee_id == employee_id, LeaveRequest.branch_id == branch_id)
        total = query.count()
        items = query.offset(skip).limit(limit).order_by(desc(LeaveRequest.created_at)).all()
        return items, total

    def get_pending(self, branch_id: UUID, skip: int = 0, limit: int = 10):
        query = self.db.query(LeaveRequest).filter(LeaveRequest.status == "pending", LeaveRequest.branch_id == branch_id)
        total = query.count()
        items = query.offset(skip).limit(limit).order_by(desc(LeaveRequest.created_at)).all()
        return items, total

    def get_by_id(self, leave_request_id: UUID, branch_id: UUID):
        return self.db.query(LeaveRequest).filter(LeaveRequest.id == leave_request_id, LeaveRequest.branch_id == branch_id).first()

    def check_overlap(self, employee_id: UUID, start_date: date, end_date: date, branch_id: UUID):
        return (
            self.db.query(LeaveRequest)
            .filter(
                LeaveRequest.employee_id == employee_id,
                LeaveRequest.start_date <= end_date,
                LeaveRequest.end_date >= start_date,
                LeaveRequest.status.in_(["pending", "approved"]),
                LeaveRequest.branch_id == branch_id,
            )
            .first()
        )

    def create(self, data: dict):
        leave_request = LeaveRequest(**data)
        self.db.add(leave_request)
        self.db.flush()
        return leave_request

    def update(self, leave_request_id: UUID, data: dict, branch_id: UUID):
        leave_request = self.get_by_id(leave_request_id, branch_id)
        if leave_request:
            for key, value in data.items():
                if value is not None:
                    setattr(leave_request, key, value)
        return leave_request


class LeaveBalanceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_employee_year(self, employee_id: UUID, financial_year: int, branch_id: UUID):
        return (
            self.db.query(LeaveBalance)
            .filter(
                LeaveBalance.employee_id == employee_id,
                LeaveBalance.financial_year == financial_year,
                LeaveBalance.branch_id == branch_id,
            )
            .all()
        )

    def get_by_employee_type_year(self, employee_id: UUID, leave_type_id: UUID, financial_year: int, branch_id: UUID):
        return (
            self.db.query(LeaveBalance)
            .filter(
                LeaveBalance.employee_id == employee_id,
                LeaveBalance.leave_type_id == leave_type_id,
                LeaveBalance.financial_year == financial_year,
                LeaveBalance.branch_id == branch_id,
            )
            .first()
        )

    def create(self, data: dict):
        balance = LeaveBalance(**data)
        self.db.add(balance)
        self.db.flush()
        return balance

    def update(self, balance_id: UUID, data: dict):
        balance = self.db.query(LeaveBalance).filter(LeaveBalance.id == balance_id).first()
        if balance:
            for key, value in data.items():
                if value is not None:
                    setattr(balance, key, value)
        return balance


class SalaryStructureRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_active_by_employee(self, employee_id: UUID, branch_id: UUID):
        today = date.today()
        return (
            self.db.query(SalaryStructure)
            .filter(
                SalaryStructure.employee_id == employee_id,
                SalaryStructure.effective_from <= today,
                or_(SalaryStructure.effective_to == None, SalaryStructure.effective_to >= today),
                SalaryStructure.branch_id == branch_id,
            )
            .first()
        )

    def get_by_employee(self, employee_id: UUID, branch_id: UUID, skip: int = 0, limit: int = 10):
        query = self.db.query(SalaryStructure).filter(
            SalaryStructure.employee_id == employee_id, SalaryStructure.branch_id == branch_id
        )
        total = query.count()
        items = query.offset(skip).limit(limit).order_by(desc(SalaryStructure.effective_from)).all()
        return items, total

    def create(self, data: dict):
        salary_structure = SalaryStructure(**data)
        self.db.add(salary_structure)
        self.db.flush()
        return salary_structure


class PayrollRunRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, branch_id: UUID, skip: int = 0, limit: int = 10):
        query = self.db.query(PayrollRun).filter(PayrollRun.branch_id == branch_id)
        total = query.count()
        items = query.offset(skip).limit(limit).order_by(desc(PayrollRun.created_at)).all()
        return items, total

    def get_by_month(self, payroll_month: str, branch_id: UUID):
        return self.db.query(PayrollRun).filter(PayrollRun.payroll_month == payroll_month, PayrollRun.branch_id == branch_id).first()

    def get_by_id(self, payroll_run_id: UUID, branch_id: UUID):
        return self.db.query(PayrollRun).filter(PayrollRun.id == payroll_run_id, PayrollRun.branch_id == branch_id).first()

    def create(self, data: dict):
        payroll_run = PayrollRun(**data)
        self.db.add(payroll_run)
        self.db.flush()
        return payroll_run

    def update(self, payroll_run_id: UUID, data: dict, branch_id: UUID):
        payroll_run = self.get_by_id(payroll_run_id, branch_id)
        if payroll_run:
            for key, value in data.items():
                if value is not None:
                    setattr(payroll_run, key, value)
        return payroll_run


class PayslipRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_payroll_employee(self, payroll_run_id: UUID, employee_id: UUID, branch_id: UUID):
        return (
            self.db.query(Payslip)
            .filter(
                Payslip.payroll_run_id == payroll_run_id,
                Payslip.employee_id == employee_id,
                Payslip.branch_id == branch_id,
            )
            .first()
        )

    def get_by_payroll_run(self, payroll_run_id: UUID, branch_id: UUID, skip: int = 0, limit: int = 50):
        query = self.db.query(Payslip).filter(Payslip.payroll_run_id == payroll_run_id, Payslip.branch_id == branch_id)
        total = query.count()
        items = query.offset(skip).limit(limit).all()
        return items, total

    def get_by_employee(self, employee_id: UUID, branch_id: UUID, skip: int = 0, limit: int = 10):
        query = self.db.query(Payslip).filter(Payslip.employee_id == employee_id, Payslip.branch_id == branch_id)
        total = query.count()
        items = query.offset(skip).limit(limit).order_by(desc(Payslip.payroll_month)).all()
        return items, total

    def create(self, data: dict):
        payslip = Payslip(**data)
        self.db.add(payslip)
        self.db.flush()
        return payslip

    def update(self, payslip_id: UUID, data: dict, branch_id: UUID):
        payslip = self.db.query(Payslip).filter(Payslip.id == payslip_id, Payslip.branch_id == branch_id).first()
        if payslip:
            for key, value in data.items():
                if value is not None:
                    setattr(payslip, key, value)
        return payslip


class OvertimeRequestRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_employee(self, employee_id: UUID, branch_id: UUID, skip: int = 0, limit: int = 10):
        query = self.db.query(OvertimeRequest).filter(
            OvertimeRequest.employee_id == employee_id, OvertimeRequest.branch_id == branch_id
        )
        total = query.count()
        items = query.offset(skip).limit(limit).order_by(desc(OvertimeRequest.created_at)).all()
        return items, total

    def get_pending(self, branch_id: UUID, skip: int = 0, limit: int = 10):
        query = self.db.query(OvertimeRequest).filter(
            OvertimeRequest.is_approved == False, OvertimeRequest.branch_id == branch_id
        )
        total = query.count()
        items = query.offset(skip).limit(limit).order_by(desc(OvertimeRequest.created_at)).all()
        return items, total

    def create(self, data: dict):
        overtime = OvertimeRequest(**data)
        self.db.add(overtime)
        self.db.flush()
        return overtime


class EmployeeLoanRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_employee(self, employee_id: UUID, branch_id: UUID):
        return (
            self.db.query(EmployeeLoan)
            .filter(
                EmployeeLoan.employee_id == employee_id,
                EmployeeLoan.branch_id == branch_id,
                EmployeeLoan.is_active == True,
            )
            .all()
        )

    def get_active_loans(self, branch_id: UUID):
        return self.db.query(EmployeeLoan).filter(EmployeeLoan.branch_id == branch_id, EmployeeLoan.is_active == True).all()

    def create(self, data: dict):
        loan = EmployeeLoan(**data)
        self.db.add(loan)
        self.db.flush()
        return loan

    def update(self, loan_id: UUID, data: dict, branch_id: UUID):
        loan = self.db.query(EmployeeLoan).filter(EmployeeLoan.id == loan_id, EmployeeLoan.branch_id == branch_id).first()
        if loan:
            for key, value in data.items():
                if value is not None:
                    setattr(loan, key, value)
        return loan


class EmployeeDeductionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_employee_month(self, employee_id: UUID, deduction_month: str, branch_id: UUID):
        return (
            self.db.query(EmployeeDeduction)
            .filter(
                EmployeeDeduction.employee_id == employee_id,
                EmployeeDeduction.deduction_month == deduction_month,
                EmployeeDeduction.branch_id == branch_id,
            )
            .all()
        )

    def create(self, data: dict):
        deduction = EmployeeDeduction(**data)
        self.db.add(deduction)
        self.db.flush()
        return deduction


class ResignationRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_employee(self, employee_id: UUID, branch_id: UUID):
        return (
            self.db.query(Resignation)
            .filter(Resignation.employee_id == employee_id, Resignation.branch_id == branch_id)
            .first()
        )

    def get_pending(self, branch_id: UUID, skip: int = 0, limit: int = 10):
        query = self.db.query(Resignation).filter(
            Resignation.status.in_(["pending", "approved"]), Resignation.branch_id == branch_id
        )
        total = query.count()
        items = query.offset(skip).limit(limit).order_by(desc(Resignation.created_at)).all()
        return items, total

    def create(self, data: dict):
        resignation = Resignation(**data)
        self.db.add(resignation)
        self.db.flush()
        return resignation

    def update(self, resignation_id: UUID, data: dict, branch_id: UUID):
        resignation = self.db.query(Resignation).filter(
            Resignation.id == resignation_id, Resignation.branch_id == branch_id
        ).first()
        if resignation:
            for key, value in data.items():
                if value is not None:
                    setattr(resignation, key, value)
        return resignation


class PerformanceReviewRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_employee(self, employee_id: UUID, branch_id: UUID, skip: int = 0, limit: int = 10):
        query = self.db.query(PerformanceReview).filter(
            PerformanceReview.employee_id == employee_id, PerformanceReview.branch_id == branch_id
        )
        total = query.count()
        items = query.offset(skip).limit(limit).order_by(desc(PerformanceReview.created_at)).all()
        return items, total

    def create(self, data: dict):
        review = PerformanceReview(**data)
        self.db.add(review)
        self.db.flush()
        return review


class RecruitmentJobRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, branch_id: UUID, skip: int = 0, limit: int = 10):
        query = self.db.query(RecruitmentJob).filter(RecruitmentJob.branch_id == branch_id, RecruitmentJob.is_active == True)
        total = query.count()
        items = query.offset(skip).limit(limit).order_by(desc(RecruitmentJob.posting_date)).all()
        return items, total

    def get_by_id(self, job_id: UUID, branch_id: UUID):
        return self.db.query(RecruitmentJob).filter(RecruitmentJob.id == job_id, RecruitmentJob.branch_id == branch_id).first()

    def create(self, data: dict):
        job = RecruitmentJob(**data)
        self.db.add(job)
        self.db.flush()
        return job


class CandidateRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_job(self, job_id: UUID, branch_id: UUID, skip: int = 0, limit: int = 10):
        query = self.db.query(Candidate).filter(Candidate.job_id == job_id, Candidate.branch_id == branch_id)
        total = query.count()
        items = query.offset(skip).limit(limit).order_by(desc(Candidate.created_at)).all()
        return items, total

    def get_by_status(self, job_id: UUID, status: str, branch_id: UUID):
        return (
            self.db.query(Candidate)
            .filter(Candidate.job_id == job_id, Candidate.status == status, Candidate.branch_id == branch_id)
            .all()
        )

    def create(self, data: dict):
        candidate = Candidate(**data)
        self.db.add(candidate)
        self.db.flush()
        return candidate

    def update(self, candidate_id: UUID, data: dict, branch_id: UUID):
        candidate = self.db.query(Candidate).filter(Candidate.id == candidate_id, Candidate.branch_id == branch_id).first()
        if candidate:
            for key, value in data.items():
                if value is not None:
                    setattr(candidate, key, value)
        return candidate
