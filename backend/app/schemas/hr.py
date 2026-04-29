from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int = 1
    page_size: int = 20


class HRDashboardSummary(BaseModel):
    total_employees: int
    active_employees: int
    inactive_employees: int
    new_joiners: int
    resigned_staff: int
    attendance: dict[str, int]
    department_counts: dict[str, int]
    category_counts: dict[str, int]
    pending_leave_requests: int
    pending_payroll_approvals: int
    monthly_salary_payable: Decimal
    alerts: list[str] = []


class HRDesignationCreate(BaseModel):
    department_id: UUID | None = None
    name: str = Field(min_length=2, max_length=150)
    code: str | None = Field(default=None, max_length=50)
    grade: str | None = Field(default=None, max_length=50)
    description: str | None = None


class HRDesignationRead(HRDesignationCreate):
    id: UUID
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class HREmployeeCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=160)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=120)
    gender: str | None = None
    date_of_birth: date | None = None
    address: str | None = None
    national_id: str | None = None
    passport_number: str | None = None
    department_id: UUID | None = None
    designation_id: UUID | None = None
    reporting_manager_id: UUID | None = None
    employee_type: str = "full_time"
    employee_category: str = "other"
    joining_date: date
    employment_status: str = "active"
    qualification: str | None = None
    specialization: str | None = None
    license_number: str | None = None
    license_expiry_date: date | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    bank_name: str | None = None
    bank_account_name: str | None = None
    bank_account_number: str | None = None
    tax_id: str | None = None
    contract_end_date: date | None = None
    photo_url: str | None = None


class HREmployeeRead(HREmployeeCreate):
    id: UUID
    staff_code: str
    is_active: bool
    created_at: datetime
    department_name: str | None = None
    designation_name: str | None = None
    salary_gross: Decimal | None = None
    model_config = {"from_attributes": True}


class HRAttendanceCreate(BaseModel):
    employee_id: UUID
    attendance_date: date
    check_in_at: datetime | None = None
    check_out_at: datetime | None = None
    status: str = "present"
    working_hours: Decimal = Decimal("0")
    late_minutes: int = 0
    early_leave_minutes: int = 0
    note: str | None = None


class HRAttendanceRead(HRAttendanceCreate):
    id: UUID
    employee_name: str | None = None
    staff_code: str | None = None
    created_at: datetime
    model_config = {"from_attributes": True}


class HRShiftCreate(BaseModel):
    name: str
    code: str
    shift_type: str = "morning"
    start_time: str
    end_time: str
    break_minutes: int = 0
    allowance_amount: Decimal = Decimal("0")


class HRShiftRead(HRShiftCreate):
    id: UUID
    is_active: bool
    model_config = {"from_attributes": True}


class HRDutyRosterCreate(BaseModel):
    employee_id: UUID
    shift_id: UUID | None = None
    roster_date: date
    duty_area: str | None = None
    duty_type: str = "regular"
    status: str = "assigned"
    note: str | None = None


class HRDutyRosterRead(HRDutyRosterCreate):
    id: UUID
    employee_name: str | None = None
    staff_code: str | None = None
    shift_name: str | None = None
    model_config = {"from_attributes": True}


class HRLeaveTypeCreate(BaseModel):
    name: str
    code: str
    annual_quota: Decimal = Decimal("0")
    is_paid: bool = True
    requires_approval: bool = True


class HRLeaveTypeRead(HRLeaveTypeCreate):
    id: UUID
    is_active: bool
    model_config = {"from_attributes": True}


class HRLeaveRequestCreate(BaseModel):
    employee_id: UUID
    leave_type_id: UUID
    start_date: date
    end_date: date
    number_of_days: Decimal
    reason: str | None = None


class HRLeaveRequestRead(HRLeaveRequestCreate):
    id: UUID
    status: str
    employee_name: str | None = None
    leave_type_name: str | None = None
    approval_remarks: str | None = None
    created_at: datetime
    model_config = {"from_attributes": True}


class HRSalaryStructureCreate(BaseModel):
    employee_id: UUID
    effective_from: date
    basic_salary: Decimal
    house_rent_allowance: Decimal = Decimal("0")
    medical_allowance: Decimal = Decimal("0")
    transport_allowance: Decimal = Decimal("0")
    food_allowance: Decimal = Decimal("0")
    night_duty_allowance: Decimal = Decimal("0")
    on_call_allowance: Decimal = Decimal("0")
    emergency_duty_allowance: Decimal = Decimal("0")
    overtime_hourly_rate: Decimal = Decimal("0")
    bonus_incentive: Decimal = Decimal("0")
    tax_deduction: Decimal = Decimal("0")
    provident_fund_deduction: Decimal = Decimal("0")
    other_deductions: Decimal = Decimal("0")


class HRSalaryStructureRead(HRSalaryStructureCreate):
    id: UUID
    employee_name: str | None = None
    gross_salary: Decimal
    total_deductions: Decimal
    net_salary: Decimal
    model_config = {"from_attributes": True}


class HROvertimeCreate(BaseModel):
    employee_id: UUID
    overtime_date: date
    overtime_hours: Decimal
    overtime_type: str = "regular"
    reason: str | None = None


class HROvertimeRead(HROvertimeCreate):
    id: UUID
    status: str
    employee_name: str | None = None
    created_at: datetime
    model_config = {"from_attributes": True}


class HRLoanCreate(BaseModel):
    employee_id: UUID
    loan_type: str = "advance"
    approved_amount: Decimal
    monthly_installment: Decimal
    deduction_start_month: str
    note: str | None = None


class HRLoanRead(HRLoanCreate):
    id: UUID
    remaining_balance: Decimal
    status: str
    employee_name: str | None = None
    model_config = {"from_attributes": True}


class HRPayrollRunCreate(BaseModel):
    payroll_month: str = Field(pattern=r"^\d{4}-\d{2}$")
    department_id: UUID | None = None
    note: str | None = None


class HRPayrollItemRead(BaseModel):
    id: UUID
    employee_id: UUID
    employee_name: str | None = None
    staff_code: str | None = None
    payroll_month: str
    present_days: Decimal
    absent_days: Decimal
    late_days: Decimal
    unpaid_leave_days: Decimal
    overtime_hours: Decimal
    gross_salary: Decimal
    total_deductions: Decimal
    net_salary: Decimal
    payment_status: str
    calculation_note: str | None = None
    model_config = {"from_attributes": True}


class HRPayrollRunRead(BaseModel):
    id: UUID
    payroll_month: str
    department_id: UUID | None = None
    status: str
    total_employees: int
    total_gross_salary: Decimal
    total_deductions: Decimal
    total_net_salary: Decimal
    created_at: datetime
    items: list[HRPayrollItemRead] = []
    model_config = {"from_attributes": True}


class HRRecruitmentJobCreate(BaseModel):
    department_id: UUID | None = None
    title: str
    number_of_positions: int = 1
    status: str = "open"
    closing_date: date | None = None
    salary_range: str | None = None
    description: str | None = None


class HRRecruitmentJobRead(HRRecruitmentJobCreate):
    id: UUID
    created_at: datetime
    model_config = {"from_attributes": True}


class HRCandidateCreate(BaseModel):
    job_id: UUID | None = None
    full_name: str
    phone: str | None = None
    email: str | None = None
    status: str = "applied"
    interview_at: datetime | None = None
    notes: str | None = None


class HRCandidateRead(HRCandidateCreate):
    id: UUID
    created_at: datetime
    model_config = {"from_attributes": True}


class HRPerformanceCreate(BaseModel):
    employee_id: UUID
    review_period: str
    rating: Decimal
    feedback: str | None = None
    kpi_summary: str | None = None
    recommendation: str | None = None


class HRPerformanceRead(HRPerformanceCreate):
    id: UUID
    employee_name: str | None = None
    created_at: datetime
    model_config = {"from_attributes": True}


class HRResignationCreate(BaseModel):
    employee_id: UUID
    resignation_date: date
    last_working_date: date | None = None
    reason: str | None = None


class HRResignationRead(HRResignationCreate):
    id: UUID
    status: str
    employee_name: str | None = None
    final_settlement_amount: Decimal
    clearance_status: str
    model_config = {"from_attributes": True}


class HRSettingRead(BaseModel):
    id: UUID
    setting_key: str
    setting_value: str | None = None
    description: str | None = None
    model_config = {"from_attributes": True}


class HRSettingUpdate(BaseModel):
    setting_value: str | None = None
    description: str | None = None
