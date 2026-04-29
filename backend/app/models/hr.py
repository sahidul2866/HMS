from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseModelMixin


class HRDesignation(Base, BaseModelMixin):
    __tablename__ = "hr_designations"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    department_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("departments.id"))
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    code: Mapped[str | None] = mapped_column(String(50))
    grade: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)

    department = relationship("Department")
    employees = relationship("HREmployee", back_populates="designation")


class HREmployee(Base, BaseModelMixin):
    __tablename__ = "hr_employees"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    staff_code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    department_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("departments.id"))
    designation_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("hr_designations.id"))
    reporting_manager_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("hr_employees.id"))
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    photo_url: Mapped[str | None] = mapped_column(String(500))
    gender: Mapped[str | None] = mapped_column(String(30))
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(120), unique=True)
    address: Mapped[str | None] = mapped_column(Text)
    national_id: Mapped[str | None] = mapped_column(String(80))
    passport_number: Mapped[str | None] = mapped_column(String(80))
    employee_type: Mapped[str] = mapped_column(String(60), nullable=False, default="full_time")
    employee_category: Mapped[str] = mapped_column(String(60), nullable=False, default="other")
    joining_date: Mapped[date] = mapped_column(Date, nullable=False)
    employment_status: Mapped[str] = mapped_column(String(40), nullable=False, default="active")
    qualification: Mapped[str | None] = mapped_column(Text)
    specialization: Mapped[str | None] = mapped_column(String(160))
    license_number: Mapped[str | None] = mapped_column(String(120))
    license_expiry_date: Mapped[date | None] = mapped_column(Date)
    emergency_contact_name: Mapped[str | None] = mapped_column(String(160))
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(30))
    bank_name: Mapped[str | None] = mapped_column(String(160))
    bank_account_name: Mapped[str | None] = mapped_column(String(160))
    bank_account_number: Mapped[str | None] = mapped_column(String(80))
    tax_id: Mapped[str | None] = mapped_column(String(80))
    contract_end_date: Mapped[date | None] = mapped_column(Date)

    branch = relationship("Branch")
    user = relationship("User", foreign_keys=[user_id])
    department = relationship("Department")
    designation = relationship("HRDesignation", back_populates="employees")
    reporting_manager = relationship("HREmployee", remote_side="HREmployee.id")
    documents = relationship("HREmployeeDocument", back_populates="employee", cascade="all, delete-orphan")
    salary_structure = relationship("HRSalaryStructure", back_populates="employee", uselist=False, cascade="all, delete-orphan")


class HREmployeeDocument(Base, BaseModelMixin):
    __tablename__ = "hr_employee_documents"

    employee_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("hr_employees.id"), nullable=False)
    document_type: Mapped[str] = mapped_column(String(80), nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(220))
    file_url: Mapped[str | None] = mapped_column(String(500))
    expiry_date: Mapped[date | None] = mapped_column(Date)
    note: Mapped[str | None] = mapped_column(Text)

    employee = relationship("HREmployee", back_populates="documents")


class HRAttendance(Base, BaseModelMixin):
    __tablename__ = "hr_attendance"
    __table_args__ = (UniqueConstraint("employee_id", "attendance_date", name="uq_hr_attendance_employee_date"),)

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    employee_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("hr_employees.id"), nullable=False)
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False)
    check_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    check_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="present")
    working_hours: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    late_minutes: Mapped[int] = mapped_column(nullable=False, default=0)
    early_leave_minutes: Mapped[int] = mapped_column(nullable=False, default=0)
    correction_status: Mapped[str | None] = mapped_column(String(40))
    correction_note: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)

    employee = relationship("HREmployee")


class HRShift(Base, BaseModelMixin):
    __tablename__ = "hr_shifts"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    shift_type: Mapped[str] = mapped_column(String(60), nullable=False, default="morning")
    start_time: Mapped[str] = mapped_column(String(10), nullable=False)
    end_time: Mapped[str] = mapped_column(String(10), nullable=False)
    break_minutes: Mapped[int] = mapped_column(nullable=False, default=0)
    allowance_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)


class HRDutyRoster(Base, BaseModelMixin):
    __tablename__ = "hr_duty_rosters"
    __table_args__ = (UniqueConstraint("employee_id", "roster_date", "shift_id", name="uq_hr_roster_employee_shift_date"),)

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    employee_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("hr_employees.id"), nullable=False)
    shift_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("hr_shifts.id"))
    roster_date: Mapped[date] = mapped_column(Date, nullable=False)
    duty_area: Mapped[str | None] = mapped_column(String(120))
    duty_type: Mapped[str] = mapped_column(String(60), nullable=False, default="regular")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="assigned")
    note: Mapped[str | None] = mapped_column(Text)

    employee = relationship("HREmployee")
    shift = relationship("HRShift")


class HRLeaveType(Base, BaseModelMixin):
    __tablename__ = "hr_leave_types"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    annual_quota: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, default=0)
    is_paid: Mapped[bool] = mapped_column(nullable=False, default=True)
    requires_approval: Mapped[bool] = mapped_column(nullable=False, default=True)


class HRLeaveRequest(Base, BaseModelMixin):
    __tablename__ = "hr_leave_requests"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    employee_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("hr_employees.id"), nullable=False)
    leave_type_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("hr_leave_types.id"), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    number_of_days: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    approved_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    approval_remarks: Mapped[str | None] = mapped_column(Text)

    employee = relationship("HREmployee")
    leave_type = relationship("HRLeaveType")


class HRSalaryStructure(Base, BaseModelMixin):
    __tablename__ = "hr_salary_structures"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    employee_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("hr_employees.id"), nullable=False, unique=True)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    basic_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    house_rent_allowance: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    medical_allowance: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    transport_allowance: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    food_allowance: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    night_duty_allowance: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    on_call_allowance: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    emergency_duty_allowance: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    overtime_hourly_rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    bonus_incentive: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    tax_deduction: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    provident_fund_deduction: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    other_deductions: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)

    employee = relationship("HREmployee", back_populates="salary_structure")


class HROvertimeRequest(Base, BaseModelMixin):
    __tablename__ = "hr_overtime_requests"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    employee_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("hr_employees.id"), nullable=False)
    overtime_date: Mapped[date] = mapped_column(Date, nullable=False)
    overtime_hours: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    overtime_type: Mapped[str] = mapped_column(String(60), nullable=False, default="regular")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    reason: Mapped[str | None] = mapped_column(Text)
    approved_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))

    employee = relationship("HREmployee")


class HREmployeeLoan(Base, BaseModelMixin):
    __tablename__ = "hr_employee_loans"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    employee_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("hr_employees.id"), nullable=False)
    loan_type: Mapped[str] = mapped_column(String(60), nullable=False, default="advance")
    approved_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    monthly_installment: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    deduction_start_month: Mapped[str] = mapped_column(String(7), nullable=False)
    remaining_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="active")
    note: Mapped[str | None] = mapped_column(Text)

    employee = relationship("HREmployee")


class HRPayrollRun(Base, BaseModelMixin):
    __tablename__ = "hr_payroll_runs"
    __table_args__ = (UniqueConstraint("branch_id", "payroll_month", "department_id", name="uq_hr_payroll_month_department"),)

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    department_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("departments.id"))
    payroll_month: Mapped[str] = mapped_column(String(7), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft")
    total_employees: Mapped[int] = mapped_column(nullable=False, default=0)
    total_gross_salary: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    total_deductions: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    total_net_salary: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    approved_by_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    note: Mapped[str | None] = mapped_column(Text)

    items = relationship("HRPayrollItem", back_populates="payroll_run", cascade="all, delete-orphan")


class HRPayrollItem(Base, BaseModelMixin):
    __tablename__ = "hr_payroll_items"

    payroll_run_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("hr_payroll_runs.id"), nullable=False)
    employee_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("hr_employees.id"), nullable=False)
    payroll_month: Mapped[str] = mapped_column(String(7), nullable=False)
    present_days: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, default=0)
    absent_days: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, default=0)
    late_days: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, default=0)
    unpaid_leave_days: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False, default=0)
    overtime_hours: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    basic_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_allowances: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    overtime_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    gross_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    tax_deduction: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    provident_fund_deduction: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    loan_deduction: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    attendance_deduction: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    other_deductions: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_deductions: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    net_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    payment_status: Mapped[str] = mapped_column(String(40), nullable=False, default="unpaid")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    calculation_note: Mapped[str | None] = mapped_column(Text)

    payroll_run = relationship("HRPayrollRun", back_populates="items")
    employee = relationship("HREmployee")


class HRRecruitmentJob(Base, BaseModelMixin):
    __tablename__ = "hr_recruitment_jobs"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    department_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("departments.id"))
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    number_of_positions: Mapped[int] = mapped_column(nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="open")
    closing_date: Mapped[date | None] = mapped_column(Date)
    salary_range: Mapped[str | None] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)


class HRCandidate(Base, BaseModelMixin):
    __tablename__ = "hr_candidates"

    job_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("hr_recruitment_jobs.id"))
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30))
    email: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="applied")
    interview_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)

    job = relationship("HRRecruitmentJob")


class HRPerformanceReview(Base, BaseModelMixin):
    __tablename__ = "hr_performance_reviews"

    employee_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("hr_employees.id"), nullable=False)
    review_period: Mapped[str] = mapped_column(String(20), nullable=False)
    rating: Mapped[Decimal] = mapped_column(Numeric(3, 1), nullable=False, default=3)
    feedback: Mapped[str | None] = mapped_column(Text)
    kpi_summary: Mapped[str | None] = mapped_column(Text)
    recommendation: Mapped[str | None] = mapped_column(Text)

    employee = relationship("HREmployee")


class HRResignation(Base, BaseModelMixin):
    __tablename__ = "hr_resignations"

    employee_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("hr_employees.id"), nullable=False)
    resignation_date: Mapped[date] = mapped_column(Date, nullable=False)
    last_working_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="applied")
    reason: Mapped[str | None] = mapped_column(Text)
    exit_interview_note: Mapped[str | None] = mapped_column(Text)
    final_settlement_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    clearance_status: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")

    employee = relationship("HREmployee")


class HRLetter(Base, BaseModelMixin):
    __tablename__ = "hr_letters"

    employee_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("hr_employees.id"))
    letter_type: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="draft")


class HRSetting(Base, BaseModelMixin):
    __tablename__ = "hr_settings"
    __table_args__ = (UniqueConstraint("branch_id", "setting_key", name="uq_hr_settings_branch_key"),)

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    setting_key: Mapped[str] = mapped_column(String(100), nullable=False)
    setting_value: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)


class HRAuditLog(Base, BaseModelMixin):
    __tablename__ = "hr_audit_logs"

    branch_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("branches.id"))
    actor_user_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(80))
    detail: Mapped[str | None] = mapped_column(Text)
