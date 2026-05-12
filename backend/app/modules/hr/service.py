from calendar import monthrange
from datetime import UTC, date, datetime
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import AppException
from app.models.department import Department
from app.models.hr import (
    HRAttendance,
    HRAuditLog,
    HRCandidate,
    HRDesignation,
    HRDutyRoster,
    HREmployee,
    HREmployeeDocument,
    HREmployeeLoan,
    HRLeaveRequest,
    HRLeaveType,
    HROvertimeRequest,
    HRPayrollItem,
    HRPayrollRun,
    HRPerformanceReview,
    HRRecruitmentJob,
    HRResignation,
    HRSalaryStructure,
    HRSetting,
    HRShift,
)
from app.models.user import User
from app.schemas.hr import (
    HRAttendanceCreate,
    HRCandidateCreate,
    HRDashboardSummary,
    HRDesignationCreate,
    HRDutyRosterCreate,
    HREmployeeCreate,
    HREmployeeDocumentCreate,
    HRPayrollDashboard,
    HRReportSummary,
    HRLeaveRequestCreate,
    HRLeaveTypeCreate,
    HRLoanCreate,
    HROvertimeCreate,
    HRPayrollRunCreate,
    HRPayrollRunRead,
    HRPerformanceCreate,
    HRRecruitmentJobCreate,
    HRResignationCreate,
    HRSalaryStructureCreate,
    HRSettingUpdate,
    HRShiftCreate,
)

TWOPLACES = Decimal("0.01")


class HRService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def dashboard(self, actor: User) -> HRDashboardSummary:
        today = date.today()
        month_prefix = today.strftime("%Y-%m")
        employees = self.list_employees(actor, page=1, page_size=10000)[0]
        active = [item for item in employees if item.employment_status == "active" and item.is_active]
        attendance_rows = self.list_attendance(actor, attendance_date=today)
        payroll_due = self.db.scalar(
            select(func.coalesce(func.sum(HRPayrollRun.total_net_salary), 0)).where(
                HRPayrollRun.branch_id == actor.branch_id,
                HRPayrollRun.payroll_month == month_prefix,
                HRPayrollRun.status.in_(["draft", "approved", "finalized"]),
            )
        )
        current_run = self.db.scalar(
            select(HRPayrollRun).where(HRPayrollRun.branch_id == actor.branch_id, HRPayrollRun.payroll_month == month_prefix).order_by(HRPayrollRun.created_at.desc()).limit(1)
        )
        overtime_cost = Decimal("0")
        deduction_total = Decimal("0")
        if current_run:
            overtime_cost = sum((item.overtime_amount for item in current_run.items), Decimal("0"))
            deduction_total = sum((item.total_deductions for item in current_run.items), Decimal("0"))
        department_counts: dict[str, int] = {}
        category_counts: dict[str, int] = {}
        alerts: list[str] = []
        expiring_document_count = 0
        for employee in employees:
            department_counts[employee.department.name if employee.department else "Unassigned"] = department_counts.get(employee.department.name if employee.department else "Unassigned", 0) + 1
            category_counts[employee.employee_category] = category_counts.get(employee.employee_category, 0) + 1
            if employee.license_expiry_date and (employee.license_expiry_date - today).days <= 45:
                alerts.append(f"{employee.full_name} license expires on {employee.license_expiry_date}")
            if employee.contract_end_date and (employee.contract_end_date - today).days <= 45:
                alerts.append(f"{employee.full_name} contract expires on {employee.contract_end_date}")
            for document in employee.documents:
                if document.expiry_date and 0 <= (document.expiry_date - today).days <= 45:
                    expiring_document_count += 1
                    alerts.append(f"{employee.full_name} {document.document_type} expires on {document.expiry_date}")
        return HRDashboardSummary(
            total_employees=len(employees),
            active_employees=len(active),
            inactive_employees=len([item for item in employees if item.employment_status in {"inactive", "terminated"}]),
            new_joiners=len([item for item in employees if item.joining_date.strftime("%Y-%m") == month_prefix]),
            resigned_staff=len([item for item in employees if item.employment_status == "resigned"]),
            attendance={
                "present": len([item for item in attendance_rows if item.status == "present"]),
                "late": len([item for item in attendance_rows if item.status == "late"]),
                "absent": len([item for item in attendance_rows if item.status == "absent"]),
                "on_leave": len([item for item in attendance_rows if item.status == "on_leave"]),
                "half_day": len([item for item in attendance_rows if item.status == "half_day"]),
            },
            department_counts=department_counts,
            category_counts=category_counts,
            pending_leave_requests=self.db.scalar(select(func.count(HRLeaveRequest.id)).where(HRLeaveRequest.branch_id == actor.branch_id, HRLeaveRequest.status == "pending")) or 0,
            pending_payroll_approvals=self.db.scalar(select(func.count(HRPayrollRun.id)).where(HRPayrollRun.branch_id == actor.branch_id, HRPayrollRun.status == "draft")) or 0,
            monthly_salary_payable=self._money(Decimal(payroll_due or 0)),
            employees_on_leave=len([item for item in attendance_rows if item.status == "on_leave"]),
            expiring_documents=expiring_document_count,
            current_month_payroll_status=current_run.status if current_run else None,
            total_overtime_cost=self._money(overtime_cost),
            total_deductions=self._money(deduction_total),
            alerts=alerts[:8],
        )

    def list_employees(self, actor: User, *, page: int, page_size: int, q: str | None = None, status: str | None = None) -> tuple[list[HREmployee], int]:
        stmt = (
            select(HREmployee)
            .options(
                selectinload(HREmployee.department),
                selectinload(HREmployee.designation),
                selectinload(HREmployee.reporting_manager),
                selectinload(HREmployee.documents),
                selectinload(HREmployee.salary_structure),
            )
            .where(HREmployee.branch_id == actor.branch_id)
            .order_by(HREmployee.created_at.desc())
        )
        if q:
            pattern = f"%{q.strip()}%"
            stmt = stmt.where(or_(HREmployee.staff_code.ilike(pattern), HREmployee.full_name.ilike(pattern), HREmployee.phone.ilike(pattern), HREmployee.email.ilike(pattern)))
        if status:
            stmt = stmt.where(HREmployee.employment_status == status)
        return self._paginate(stmt, page, page_size)

    def create_employee(self, payload: HREmployeeCreate, actor: User) -> HREmployee:
        employee = HREmployee(
            **payload.model_dump(),
            branch_id=actor.branch_id,
            staff_code=self._next_staff_code(actor),
            created_by=actor.id,
            updated_by=actor.id,
        )
        self.db.add(employee)
        self._audit(actor, "employee.create", "hr_employee", None, employee.full_name)
        self.db.commit()
        self.db.refresh(employee)
        return employee

    def update_employee(self, employee_id: UUID, payload: HREmployeeCreate, actor: User) -> HREmployee:
        employee = self._get_employee(employee_id, actor)
        if employee.employment_status in {"terminated", "resigned"} and payload.employment_status == "active":
            raise AppException(409, "hr_employee_reactivation_blocked", "Use a formal rehire workflow before reactivating resigned or terminated employees")
        for key, value in payload.model_dump().items():
            setattr(employee, key, value)
        employee.updated_by = actor.id
        self._audit(actor, "employee.update", "hr_employee", str(employee.id), employee.full_name)
        self.db.commit()
        self.db.refresh(employee)
        return employee

    def list_documents(self, actor: User, *, employee_id: UUID | None = None, status: str | None = None) -> list[HREmployeeDocument]:
        stmt = (
            select(HREmployeeDocument)
            .options(selectinload(HREmployeeDocument.employee))
            .join(HREmployeeDocument.employee)
            .where(HREmployee.branch_id == actor.branch_id, HREmployeeDocument.is_active.is_(True))
            .order_by(HREmployeeDocument.expiry_date.asc().nulls_last(), HREmployeeDocument.created_at.desc())
        )
        if employee_id:
            stmt = stmt.where(HREmployeeDocument.employee_id == employee_id)
        documents = list(self.db.scalars(stmt))
        if status:
            documents = [document for document in documents if self._document_status(document) == status]
        return documents

    def create_document(self, payload: HREmployeeDocumentCreate, actor: User) -> HREmployeeDocument:
        employee = self._get_employee(payload.employee_id, actor)
        document = HREmployeeDocument(**payload.model_dump(), created_by=actor.id, updated_by=actor.id)
        self.db.add(document)
        self._audit(actor, "document.create", "hr_employee_document", None, f"{employee.full_name}: {payload.document_type}")
        self.db.commit()
        self.db.refresh(document)
        return document

    def delete_document(self, document_id: UUID, actor: User) -> None:
        document = self.db.get(HREmployeeDocument, document_id)
        if not document:
            raise AppException(404, "hr_document_not_found", "Employee document not found")
        employee = self._get_employee(document.employee_id, actor)
        document.is_active = False
        document.updated_by = actor.id
        self._audit(actor, "document.delete", "hr_employee_document", str(document.id), employee.full_name)
        self.db.commit()

    def list_designations(self, actor: User) -> list[HRDesignation]:
        return list(self.db.scalars(select(HRDesignation).where(HRDesignation.branch_id == actor.branch_id, HRDesignation.is_active.is_(True)).order_by(HRDesignation.name)))

    def create_designation(self, payload: HRDesignationCreate, actor: User) -> HRDesignation:
        entity = HRDesignation(**payload.model_dump(), branch_id=actor.branch_id, created_by=actor.id, updated_by=actor.id)
        self.db.add(entity)
        self._audit(actor, "designation.create", "hr_designation", None, entity.name)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def list_attendance(self, actor: User, *, attendance_date: date | None = None, employee_id: UUID | None = None, status: str | None = None) -> list[HRAttendance]:
        stmt = select(HRAttendance).options(selectinload(HRAttendance.employee).selectinload(HREmployee.department)).where(HRAttendance.branch_id == actor.branch_id).order_by(HRAttendance.attendance_date.desc())
        if attendance_date:
            stmt = stmt.where(HRAttendance.attendance_date == attendance_date)
        if employee_id:
            stmt = stmt.where(HRAttendance.employee_id == employee_id)
        if status:
            stmt = stmt.where(HRAttendance.status == status)
        return list(self.db.scalars(stmt))

    def mark_attendance(self, payload: HRAttendanceCreate, actor: User) -> HRAttendance:
        existing = self.db.scalar(select(HRAttendance).where(HRAttendance.employee_id == payload.employee_id, HRAttendance.attendance_date == payload.attendance_date))
        if existing:
            for key, value in payload.model_dump().items():
                setattr(existing, key, value)
            existing.updated_by = actor.id
            attendance = existing
        else:
            attendance = HRAttendance(**payload.model_dump(), branch_id=actor.branch_id, created_by=actor.id, updated_by=actor.id)
            self.db.add(attendance)
        self._audit(actor, "attendance.mark", "hr_attendance", str(attendance.id) if attendance.id else None, payload.status)
        self.db.commit()
        self.db.refresh(attendance)
        return attendance

    def list_shifts(self, actor: User) -> list[HRShift]:
        return list(self.db.scalars(select(HRShift).where(HRShift.branch_id == actor.branch_id, HRShift.is_active.is_(True)).order_by(HRShift.start_time)))

    def create_shift(self, payload: HRShiftCreate, actor: User) -> HRShift:
        shift = HRShift(**payload.model_dump(), branch_id=actor.branch_id, created_by=actor.id, updated_by=actor.id)
        self.db.add(shift)
        self._audit(actor, "shift.create", "hr_shift", None, shift.name)
        self.db.commit()
        self.db.refresh(shift)
        return shift

    def list_roster(self, actor: User) -> list[HRDutyRoster]:
        return list(self.db.scalars(select(HRDutyRoster).options(selectinload(HRDutyRoster.employee), selectinload(HRDutyRoster.shift)).where(HRDutyRoster.branch_id == actor.branch_id).order_by(HRDutyRoster.roster_date.desc())))

    def create_roster(self, payload: HRDutyRosterCreate, actor: User) -> HRDutyRoster:
        conflict = self.db.scalar(select(HRDutyRoster).where(HRDutyRoster.employee_id == payload.employee_id, HRDutyRoster.roster_date == payload.roster_date, HRDutyRoster.shift_id == payload.shift_id))
        if conflict:
            raise AppException(409, "hr_roster_conflict", "Employee already has this shift on the selected date")
        roster = HRDutyRoster(**payload.model_dump(), branch_id=actor.branch_id, created_by=actor.id, updated_by=actor.id)
        self.db.add(roster)
        self._audit(actor, "roster.create", "hr_roster", None, str(payload.roster_date))
        self.db.commit()
        self.db.refresh(roster)
        return roster

    def list_leave_types(self, actor: User) -> list[HRLeaveType]:
        return list(self.db.scalars(select(HRLeaveType).where(HRLeaveType.branch_id == actor.branch_id, HRLeaveType.is_active.is_(True)).order_by(HRLeaveType.name)))

    def create_leave_type(self, payload: HRLeaveTypeCreate, actor: User) -> HRLeaveType:
        leave_type = HRLeaveType(**payload.model_dump(), branch_id=actor.branch_id, created_by=actor.id, updated_by=actor.id)
        self.db.add(leave_type)
        self.db.commit()
        self.db.refresh(leave_type)
        return leave_type

    def list_leave_requests(self, actor: User) -> list[HRLeaveRequest]:
        return list(self.db.scalars(select(HRLeaveRequest).options(selectinload(HRLeaveRequest.employee), selectinload(HRLeaveRequest.leave_type)).where(HRLeaveRequest.branch_id == actor.branch_id).order_by(HRLeaveRequest.created_at.desc())))

    def request_leave(self, payload: HRLeaveRequestCreate, actor: User) -> HRLeaveRequest:
        if payload.end_date < payload.start_date:
            raise AppException(422, "hr_leave_invalid_dates", "Leave end date cannot be before start date")
        request = HRLeaveRequest(**payload.model_dump(), branch_id=actor.branch_id, created_by=actor.id, updated_by=actor.id)
        self.db.add(request)
        self._audit(actor, "leave.request", "hr_leave_request", None, str(payload.number_of_days))
        self.db.commit()
        self.db.refresh(request)
        return request

    def decide_leave(self, request_id: UUID, actor: User, *, status: str, remarks: str | None = None) -> HRLeaveRequest:
        request = self.db.get(HRLeaveRequest, request_id)
        if not request or request.branch_id != actor.branch_id:
            raise AppException(404, "hr_leave_not_found", "Leave request not found")
        request.status = status
        request.approved_by_user_id = actor.id
        request.approval_remarks = remarks
        request.updated_by = actor.id
        self._audit(actor, f"leave.{status}", "hr_leave_request", str(request.id), remarks)
        self.db.commit()
        self.db.refresh(request)
        return request

    def upsert_salary(self, payload: HRSalaryStructureCreate, actor: User) -> HRSalaryStructure:
        employee = self._get_employee(payload.employee_id, actor)
        locked_run = self.db.scalar(
            select(HRPayrollRun.id)
            .join(HRPayrollRun.items)
            .where(HRPayrollItem.employee_id == employee.id, HRPayrollRun.status.in_(["paid", "locked"]))
            .limit(1)
        )
        if locked_run:
            raise AppException(409, "salary_locked_by_payroll", "Salary structure cannot be changed after a locked or paid payroll run without an adjustment workflow")
        salary = self.db.scalar(select(HRSalaryStructure).where(HRSalaryStructure.employee_id == payload.employee_id))
        if not salary:
            salary = HRSalaryStructure(employee_id=payload.employee_id, branch_id=actor.branch_id, created_by=actor.id, updated_by=actor.id)
            self.db.add(salary)
        for key, value in payload.model_dump().items():
            setattr(salary, key, value)
        salary.updated_by = actor.id
        self._audit(actor, "salary.upsert", "hr_salary_structure", str(salary.id) if salary.id else None, str(payload.basic_salary))
        self.db.commit()
        self.db.refresh(salary)
        return salary

    def list_salary_structures(self, actor: User) -> list[HRSalaryStructure]:
        return list(
            self.db.scalars(
                select(HRSalaryStructure)
                .options(selectinload(HRSalaryStructure.employee))
                .where(HRSalaryStructure.branch_id == actor.branch_id)
                .order_by(HRSalaryStructure.effective_from.desc())
            )
        )

    def create_overtime(self, payload: HROvertimeCreate, actor: User) -> HROvertimeRequest:
        self._get_employee(payload.employee_id, actor)
        entity = HROvertimeRequest(**payload.model_dump(), branch_id=actor.branch_id, created_by=actor.id, updated_by=actor.id)
        self.db.add(entity)
        self._audit(actor, "overtime.create", "hr_overtime_request", None, str(payload.overtime_hours))
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def list_overtime(self, actor: User) -> list[HROvertimeRequest]:
        return list(self.db.scalars(select(HROvertimeRequest).options(selectinload(HROvertimeRequest.employee)).where(HROvertimeRequest.branch_id == actor.branch_id).order_by(HROvertimeRequest.overtime_date.desc())))

    def create_loan(self, payload: HRLoanCreate, actor: User) -> HREmployeeLoan:
        self._get_employee(payload.employee_id, actor)
        entity = HREmployeeLoan(**payload.model_dump(), branch_id=actor.branch_id, remaining_balance=payload.approved_amount, created_by=actor.id, updated_by=actor.id)
        self.db.add(entity)
        self._audit(actor, "loan.create", "hr_employee_loan", None, str(payload.approved_amount))
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def list_loans(self, actor: User) -> list[HREmployeeLoan]:
        return list(self.db.scalars(select(HREmployeeLoan).options(selectinload(HREmployeeLoan.employee)).where(HREmployeeLoan.branch_id == actor.branch_id).order_by(HREmployeeLoan.created_at.desc())))

    def list_payroll_runs(self, actor: User) -> list[HRPayrollRun]:
        return list(self.db.scalars(select(HRPayrollRun).options(selectinload(HRPayrollRun.items).selectinload(HRPayrollItem.employee)).where(HRPayrollRun.branch_id == actor.branch_id).order_by(HRPayrollRun.created_at.desc())))

    def process_payroll(self, payload: HRPayrollRunCreate, actor: User) -> HRPayrollRun:
        existing = self.db.scalar(select(HRPayrollRun).where(HRPayrollRun.branch_id == actor.branch_id, HRPayrollRun.payroll_month == payload.payroll_month, HRPayrollRun.department_id == payload.department_id))
        if existing:
            raise AppException(409, "hr_payroll_duplicate", "Payroll already exists for this month and department")
        employees, _ = self.list_employees(actor, page=1, page_size=10000, status="active")
        if payload.department_id:
            employees = [item for item in employees if item.department_id == payload.department_id]
        run = HRPayrollRun(payroll_month=payload.payroll_month, department_id=payload.department_id, branch_id=actor.branch_id, status="calculated", note=payload.note, created_by=actor.id, updated_by=actor.id)
        self.db.add(run)
        totals = Decimal("0")
        deductions = Decimal("0")
        for employee in employees:
            salary = employee.salary_structure
            if not salary:
                continue
            item = self._build_payroll_item(run, employee, salary, payload.payroll_month, actor)
            run.items.append(item)
            totals += item.gross_salary
            deductions += item.total_deductions
        run.total_employees = len(run.items)
        run.total_gross_salary = self._money(totals)
        run.total_deductions = self._money(deductions)
        run.total_net_salary = self._money(totals - deductions)
        self._audit(actor, "payroll.process", "hr_payroll_run", None, payload.payroll_month)
        self.db.commit()
        self.db.refresh(run)
        return run

    def approve_payroll(self, payroll_run_id: UUID, actor: User, *, status: str) -> HRPayrollRun:
        run = self.db.get(HRPayrollRun, payroll_run_id)
        if not run or run.branch_id != actor.branch_id:
            raise AppException(404, "hr_payroll_not_found", "Payroll run not found")
        allowed_statuses = {"draft", "calculated", "reviewed", "approved", "paid", "cancelled", "locked", "finalized"}
        if status not in allowed_statuses:
            raise AppException(422, "hr_payroll_invalid_status", "Invalid payroll status")
        if run.status in {"paid", "locked"} and status not in {"locked"}:
            raise AppException(409, "hr_payroll_locked", "Paid or locked payroll cannot be edited")
        if status == "paid" and run.status not in {"approved", "finalized"}:
            raise AppException(409, "hr_payroll_requires_approval", "Payroll must be approved before payment")
        if status == "locked" and run.status != "paid":
            raise AppException(409, "hr_payroll_lock_requires_paid", "Only paid payroll can be locked")
        run.status = status
        run.approved_by_user_id = actor.id
        if status in {"finalized", "paid", "locked"}:
            run.finalized_at = datetime.now(UTC)
        if status == "paid":
            for item in run.items:
                item.payment_status = "paid"
                item.paid_at = datetime.now(UTC)
                self._apply_loan_deductions(item, actor)
        run.updated_by = actor.id
        self._audit(actor, f"payroll.{status}", "hr_payroll_run", str(run.id), run.payroll_month)
        self.db.commit()
        self.db.refresh(run)
        return run

    def payroll_dashboard(self, actor: User, payroll_month: str | None = None) -> HRPayrollDashboard:
        month = payroll_month or date.today().strftime("%Y-%m")
        runs = list(
            self.db.scalars(
                select(HRPayrollRun)
                .options(selectinload(HRPayrollRun.items).selectinload(HRPayrollItem.employee).selectinload(HREmployee.department))
                .where(HRPayrollRun.branch_id == actor.branch_id, HRPayrollRun.payroll_month == month)
            )
        )
        latest = runs[0] if runs else None
        items = [item for run in runs for item in run.items]
        department_costs: dict[str, Decimal] = {}
        for item in items:
            department = item.employee.department.name if item.employee and item.employee.department else "Unassigned"
            department_costs[department] = department_costs.get(department, Decimal("0")) + Decimal(item.net_salary or 0)
        return HRPayrollDashboard(
            payroll_month=month,
            status=latest.status if latest else None,
            total_salary_payable=self._money(sum((Decimal(item.net_salary or 0) for item in items), Decimal("0"))),
            pending_approvals=len([run for run in runs if run.status in {"draft", "calculated", "reviewed"}]),
            paid_items=len([item for item in items if item.payment_status == "paid"]),
            unpaid_items=len([item for item in items if item.payment_status != "paid"]),
            overtime_cost=self._money(sum((Decimal(item.overtime_amount or 0) for item in items), Decimal("0"))),
            deduction_total=self._money(sum((Decimal(item.total_deductions or 0) for item in items), Decimal("0"))),
            department_costs={key: self._money(value) for key, value in department_costs.items()},
        )

    def report_summary(self, actor: User, *, date_from: date | None = None, date_to: date | None = None, payroll_month: str | None = None) -> HRReportSummary:
        start = date_from or date.today().replace(day=1)
        end = date_to or date.today()
        payroll_month = payroll_month or start.strftime("%Y-%m")
        employees, _ = self.list_employees(actor, page=1, page_size=10000)
        attendance = self.list_attendance(actor)
        attendance = [row for row in attendance if start <= row.attendance_date <= end]
        leaves = [row for row in self.list_leave_requests(actor) if row.start_date <= end and row.end_date >= start]
        overtime_hours = self.db.scalar(select(func.coalesce(func.sum(HROvertimeRequest.overtime_hours), 0)).where(HROvertimeRequest.branch_id == actor.branch_id, HROvertimeRequest.overtime_date >= start, HROvertimeRequest.overtime_date <= end)) or Decimal("0")
        payroll_net = self.db.scalar(select(func.coalesce(func.sum(HRPayrollRun.total_net_salary), 0)).where(HRPayrollRun.branch_id == actor.branch_id, HRPayrollRun.payroll_month == payroll_month)) or Decimal("0")
        loan_outstanding = self.db.scalar(select(func.coalesce(func.sum(HREmployeeLoan.remaining_balance), 0)).where(HREmployeeLoan.branch_id == actor.branch_id, HREmployeeLoan.status == "active")) or Decimal("0")
        today = date.today()
        expiring_documents = len([doc for doc in self.list_documents(actor) if doc.expiry_date and 0 <= (doc.expiry_date - today).days <= 45])
        return HRReportSummary(
            employee_count=len(employees),
            attendance_summary={status: len([row for row in attendance if row.status == status]) for status in ["present", "late", "absent", "half_day", "on_leave"]},
            leave_summary={status: len([row for row in leaves if row.status == status]) for status in ["pending", "approved", "rejected"]},
            overtime_hours=Decimal(overtime_hours),
            payroll_net_total=self._money(Decimal(payroll_net)),
            loan_outstanding=self._money(Decimal(loan_outstanding)),
            expiring_documents=expiring_documents,
            resigned_employees=len([employee for employee in employees if employee.employment_status in {"resigned", "terminated"}]),
        )

    def create_recruitment_job(self, payload: HRRecruitmentJobCreate, actor: User) -> HRRecruitmentJob:
        entity = HRRecruitmentJob(**payload.model_dump(), branch_id=actor.branch_id, created_by=actor.id, updated_by=actor.id)
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def create_candidate(self, payload: HRCandidateCreate, actor: User) -> HRCandidate:
        entity = HRCandidate(**payload.model_dump(), created_by=actor.id, updated_by=actor.id)
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def create_performance_review(self, payload: HRPerformanceCreate, actor: User) -> HRPerformanceReview:
        entity = HRPerformanceReview(**payload.model_dump(), created_by=actor.id, updated_by=actor.id)
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def create_resignation(self, payload: HRResignationCreate, actor: User) -> HRResignation:
        entity = HRResignation(**payload.model_dump(), created_by=actor.id, updated_by=actor.id)
        employee = self._get_employee(payload.employee_id, actor)
        employee.employment_status = "resigned"
        self.db.add(entity)
        self.db.commit()
        self.db.refresh(entity)
        return entity

    def list_settings(self, actor: User) -> list[HRSetting]:
        self.ensure_default_settings(actor)
        return list(self.db.scalars(select(HRSetting).where(HRSetting.branch_id == actor.branch_id).order_by(HRSetting.setting_key)))

    def update_setting(self, setting_key: str, payload: HRSettingUpdate, actor: User) -> HRSetting:
        setting = self.db.scalar(select(HRSetting).where(HRSetting.branch_id == actor.branch_id, HRSetting.setting_key == setting_key))
        if not setting:
            setting = HRSetting(branch_id=actor.branch_id, setting_key=setting_key, created_by=actor.id, updated_by=actor.id)
            self.db.add(setting)
        setting.setting_value = payload.setting_value
        setting.description = payload.description
        setting.updated_by = actor.id
        self.db.commit()
        self.db.refresh(setting)
        return setting

    def ensure_default_settings(self, actor: User) -> None:
        defaults = {
            "staff_code_prefix": ("EMP", "Prefix used for generated employee staff codes."),
            "monthly_working_days": ("26", "Default payroll working days used for attendance deduction."),
            "late_deduction_enabled": ("true", "Enable payroll deductions for late attendance."),
            "license_expiry_alert_days": ("45", "Alert window for professional license expiry."),
            "contract_expiry_alert_days": ("45", "Alert window for contract expiry."),
            "payroll_requires_approval": ("true", "Payroll must be approved before finalization."),
        }
        for key, (value, description) in defaults.items():
            if not self.db.scalar(select(HRSetting).where(HRSetting.branch_id == actor.branch_id, HRSetting.setting_key == key)):
                self.db.add(HRSetting(branch_id=actor.branch_id, setting_key=key, setting_value=value, description=description, created_by=actor.id, updated_by=actor.id))
        self.db.flush()

    def _build_payroll_item(self, run: HRPayrollRun, employee: HREmployee, salary: HRSalaryStructure, payroll_month: str, actor: User) -> HRPayrollItem:
        year, month = [int(part) for part in payroll_month.split("-")]
        start = date(year, month, 1)
        end = date(year, month, monthrange(year, month)[1])
        attendance = list(self.db.scalars(select(HRAttendance).where(HRAttendance.employee_id == employee.id, HRAttendance.attendance_date >= start, HRAttendance.attendance_date <= end)))
        overtime = self.db.scalar(select(func.coalesce(func.sum(HROvertimeRequest.overtime_hours), 0)).where(HROvertimeRequest.employee_id == employee.id, HROvertimeRequest.overtime_date >= start, HROvertimeRequest.overtime_date <= end, HROvertimeRequest.status == "approved"))
        present = Decimal(len([item for item in attendance if item.status in {"present", "late"}]))
        absent = Decimal(len([item for item in attendance if item.status == "absent"]))
        late = Decimal(len([item for item in attendance if item.status == "late"]))
        unpaid_leave_attendance = Decimal(len([item for item in attendance if item.status == "on_leave"]))
        unpaid_leave_requests = self.db.scalar(
            select(func.coalesce(func.sum(HRLeaveRequest.number_of_days), 0))
            .join(HRLeaveRequest.leave_type)
            .where(
                HRLeaveRequest.employee_id == employee.id,
                HRLeaveRequest.status == "approved",
                HRLeaveRequest.start_date <= end,
                HRLeaveRequest.end_date >= start,
                HRLeaveType.is_paid.is_(False),
            )
        ) or Decimal("0")
        unpaid_leave = max(unpaid_leave_attendance, Decimal(unpaid_leave_requests))
        shift_allowance = self.db.scalar(
            select(func.coalesce(func.sum(HRShift.allowance_amount), 0))
            .join(HRDutyRoster, HRDutyRoster.shift_id == HRShift.id)
            .where(HRDutyRoster.employee_id == employee.id, HRDutyRoster.roster_date >= start, HRDutyRoster.roster_date <= end, HRDutyRoster.status.in_(["assigned", "completed", "approved"]))
        ) or Decimal("0")
        base_allowances = salary.house_rent_allowance + salary.medical_allowance + salary.transport_allowance + salary.food_allowance + salary.night_duty_allowance + salary.on_call_allowance + salary.emergency_duty_allowance + salary.bonus_incentive
        overtime_amount = Decimal(overtime or 0) * salary.overtime_hourly_rate
        per_day = salary.basic_salary / Decimal("26")
        attendance_deduction = (absent + unpaid_leave + (late * Decimal("0.25"))) * per_day
        loan_deduction = self.db.scalar(select(func.coalesce(func.sum(HREmployeeLoan.monthly_installment), 0)).where(HREmployeeLoan.employee_id == employee.id, HREmployeeLoan.status == "active", HREmployeeLoan.deduction_start_month <= payroll_month))
        gross = self._money(salary.basic_salary + base_allowances + overtime_amount + Decimal(shift_allowance or 0))
        total_deduction = self._money(salary.tax_deduction + salary.provident_fund_deduction + salary.other_deductions + Decimal(loan_deduction or 0) + attendance_deduction)
        return HRPayrollItem(
            employee_id=employee.id,
            payroll_month=payroll_month,
            present_days=present,
            absent_days=absent,
            late_days=late,
            unpaid_leave_days=unpaid_leave,
            overtime_hours=Decimal(overtime or 0),
            basic_salary=salary.basic_salary,
            total_allowances=self._money(base_allowances + Decimal(shift_allowance or 0)),
            overtime_amount=self._money(overtime_amount),
            gross_salary=gross,
            tax_deduction=salary.tax_deduction,
            provident_fund_deduction=salary.provident_fund_deduction,
            loan_deduction=self._money(Decimal(loan_deduction or 0)),
            attendance_deduction=self._money(attendance_deduction),
            other_deductions=salary.other_deductions,
            total_deductions=total_deduction,
            net_salary=self._money(gross - total_deduction),
            calculation_note=f"{present} present, {absent} absent, {late} late, {overtime or 0} OT hours",
            created_by=actor.id,
            updated_by=actor.id,
        )

    def _apply_loan_deductions(self, item: HRPayrollItem, actor: User) -> None:
        if Decimal(item.loan_deduction or 0) <= 0:
            return
        remaining_to_apply = Decimal(item.loan_deduction)
        loans = list(
            self.db.scalars(
                select(HREmployeeLoan)
                .where(HREmployeeLoan.employee_id == item.employee_id, HREmployeeLoan.status == "active", HREmployeeLoan.remaining_balance > 0)
                .order_by(HREmployeeLoan.deduction_start_month.asc(), HREmployeeLoan.created_at.asc())
            )
        )
        for loan in loans:
            if remaining_to_apply <= 0:
                break
            applied = min(Decimal(loan.remaining_balance), remaining_to_apply)
            loan.remaining_balance = Decimal(loan.remaining_balance) - applied
            if loan.remaining_balance <= 0:
                loan.remaining_balance = Decimal("0")
                loan.status = "closed"
            loan.updated_by = actor.id
            remaining_to_apply -= applied

    def _get_employee(self, employee_id: UUID, actor: User) -> HREmployee:
        employee = self.db.get(HREmployee, employee_id)
        if not employee or employee.branch_id != actor.branch_id:
            raise AppException(404, "hr_employee_not_found", "Employee not found")
        return employee

    def _next_staff_code(self, actor: User) -> str:
        prefix = "EMP"
        count = self.db.scalar(select(func.count(HREmployee.id)).where(HREmployee.branch_id == actor.branch_id)) or 0
        return f"{prefix}-{int(count) + 1001}"

    def _paginate(self, stmt, page: int, page_size: int):
        page = max(page, 1)
        page_size = min(max(page_size, 1), 10000)
        total = self.db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        items = list(self.db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).unique())
        return items, total

    def _audit(self, actor: User, action: str, entity_type: str, entity_id: str | None, detail: str | None = None) -> None:
        self.db.add(HRAuditLog(branch_id=actor.branch_id, actor_user_id=actor.id, action=action, entity_type=entity_type, entity_id=entity_id, detail=detail, created_by=actor.id, updated_by=actor.id))

    def _money(self, value: Decimal) -> Decimal:
        return Decimal(value or 0).quantize(TWOPLACES, rounding=ROUND_HALF_UP)

    def _document_status(self, document: HREmployeeDocument) -> str:
        if document.expiry_date is None:
            return "valid"
        days = (document.expiry_date - date.today()).days
        if days < 0:
            return "expired"
        if days <= 45:
            return "expiring"
        return "valid"


def serialize_employee(employee: HREmployee) -> dict:
    data = {column.name: getattr(employee, column.name) for column in employee.__table__.columns}
    data["department_name"] = employee.department.name if employee.department else None
    data["designation_name"] = employee.designation.name if employee.designation else None
    data["reporting_manager_name"] = employee.reporting_manager.full_name if employee.reporting_manager else None
    data["document_count"] = len([document for document in employee.documents if document.is_active])
    today = date.today()
    data["expiring_document_count"] = len([document for document in employee.documents if document.is_active and document.expiry_date and 0 <= (document.expiry_date - today).days <= 45])
    data["salary_gross"] = None
    if employee.salary_structure:
        salary = employee.salary_structure
        data["salary_gross"] = salary.basic_salary + salary.house_rent_allowance + salary.medical_allowance + salary.transport_allowance + salary.food_allowance + salary.night_duty_allowance + salary.on_call_allowance + salary.emergency_duty_allowance + salary.bonus_incentive
    return data


def serialize_attendance(item: HRAttendance) -> dict:
    data = {column.name: getattr(item, column.name) for column in item.__table__.columns}
    data["employee_name"] = item.employee.full_name if item.employee else None
    data["staff_code"] = item.employee.staff_code if item.employee else None
    data["department_name"] = item.employee.department.name if item.employee and item.employee.department else None
    return data


def serialize_document(item: HREmployeeDocument) -> dict:
    data = {column.name: getattr(item, column.name) for column in item.__table__.columns}
    data["employee_name"] = item.employee.full_name if item.employee else None
    data["staff_code"] = item.employee.staff_code if item.employee else None
    if item.expiry_date is None:
        data["status"] = "valid"
        data["days_to_expiry"] = None
    else:
        days = (item.expiry_date - date.today()).days
        data["days_to_expiry"] = days
        data["status"] = "expired" if days < 0 else ("expiring" if days <= 45 else "valid")
    return data


def serialize_roster(item: HRDutyRoster) -> dict:
    data = {column.name: getattr(item, column.name) for column in item.__table__.columns}
    data["employee_name"] = item.employee.full_name if item.employee else None
    data["staff_code"] = item.employee.staff_code if item.employee else None
    data["shift_name"] = item.shift.name if item.shift else None
    return data


def serialize_leave(item: HRLeaveRequest) -> dict:
    data = {column.name: getattr(item, column.name) for column in item.__table__.columns}
    data["employee_name"] = item.employee.full_name if item.employee else None
    data["leave_type_name"] = item.leave_type.name if item.leave_type else None
    data["leave_type_paid"] = item.leave_type.is_paid if item.leave_type else None
    return data


def serialize_salary(item: HRSalaryStructure) -> dict:
    data = {column.name: getattr(item, column.name) for column in item.__table__.columns}
    data["employee_name"] = item.employee.full_name if item.employee else None
    gross = item.basic_salary + item.house_rent_allowance + item.medical_allowance + item.transport_allowance + item.food_allowance + item.night_duty_allowance + item.on_call_allowance + item.emergency_duty_allowance + item.bonus_incentive
    deduction = item.tax_deduction + item.provident_fund_deduction + item.other_deductions
    data["gross_salary"] = gross
    data["total_deductions"] = deduction
    data["net_salary"] = gross - deduction
    return data


def serialize_payroll_run(run: HRPayrollRun) -> HRPayrollRunRead:
    return HRPayrollRunRead(
        id=run.id,
        payroll_month=run.payroll_month,
        department_id=run.department_id,
        status=run.status,
        total_employees=run.total_employees,
        total_gross_salary=run.total_gross_salary,
        total_deductions=run.total_deductions,
        total_net_salary=run.total_net_salary,
        created_at=run.created_at,
        items=[
            {
                "id": item.id,
                "employee_id": item.employee_id,
                "employee_name": item.employee.full_name if item.employee else None,
                "staff_code": item.employee.staff_code if item.employee else None,
                "payroll_month": item.payroll_month,
                "present_days": item.present_days,
                "absent_days": item.absent_days,
                "late_days": item.late_days,
                "unpaid_leave_days": item.unpaid_leave_days,
                "overtime_hours": item.overtime_hours,
                "gross_salary": item.gross_salary,
                "total_deductions": item.total_deductions,
                "net_salary": item.net_salary,
                "payment_status": item.payment_status,
                "calculation_note": item.calculation_note,
            }
            for item in run.items
        ],
    )
