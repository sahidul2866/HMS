from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.permissions import require_permissions
from app.modules.hr.service import HRService, serialize_attendance, serialize_document, serialize_employee, serialize_leave, serialize_roster, serialize_salary
from app.schemas.hr import (
    HRAttendanceCreate,
    HRAttendanceRead,
    HRDashboardSummary,
    HRDesignationCreate,
    HRDesignationRead,
    HRDutyRosterCreate,
    HRDutyRosterRead,
    HREmployeeCreate,
    HREmployeeDocumentCreate,
    HREmployeeDocumentRead,
    HREmployeeRead,
    HRLeaveRequestCreate,
    HRLeaveRequestRead,
    HRLeaveTypeCreate,
    HRLeaveTypeRead,
    HRLoanCreate,
    HRLoanRead,
    HROvertimeCreate,
    HROvertimeRead,
    HRPayrollDashboard,
    HRPayrollRunCreate,
    HRPayrollRunRead,
    HRReportSummary,
    HRRecruitmentJobCreate,
    HRResignationCreate,
    HRSalaryStructureCreate,
    HRSalaryStructureRead,
    HRSettingRead,
    HRSettingUpdate,
    HRShiftCreate,
    HRShiftRead,
    PaginatedResponse,
    HRCandidateCreate,
    HRPerformanceCreate,
)

router = APIRouter(prefix="/hr", tags=["HR & Payroll"])


def _salary_payload(salary) -> dict:
    data = {column.name: getattr(salary, column.name) for column in salary.__table__.columns}
    data["employee_name"] = salary.employee.full_name if salary.employee else None
    allowances = (
        salary.house_rent_allowance
        + salary.medical_allowance
        + salary.transport_allowance
        + salary.food_allowance
        + salary.night_duty_allowance
        + salary.on_call_allowance
        + salary.emergency_duty_allowance
        + salary.bonus_incentive
    )
    data["gross_salary"] = salary.basic_salary + allowances
    data["total_deductions"] = salary.tax_deduction + salary.provident_fund_deduction + salary.other_deductions
    data["net_salary"] = data["gross_salary"] - data["total_deductions"]
    return data


def _payroll_item_payload(item) -> dict:
    data = {column.name: getattr(item, column.name) for column in item.__table__.columns}
    data["employee_name"] = item.employee.full_name if item.employee else None
    data["staff_code"] = item.employee.staff_code if item.employee else None
    return data


def _payroll_run_payload(run) -> dict:
    data = {column.name: getattr(run, column.name) for column in run.__table__.columns}
    data["items"] = [_payroll_item_payload(item) for item in run.items]
    return data


def _named_payload(item, relation_name: str = "employee") -> dict:
    data = {column.name: getattr(item, column.name) for column in item.__table__.columns}
    employee = getattr(item, relation_name, None)
    if employee:
        data["employee_name"] = employee.full_name
    return data


@router.get("/dashboard", response_model=HRDashboardSummary, dependencies=[Depends(require_permissions("hr.view"))])
def dashboard(user=Depends(get_current_user), db: Session = Depends(get_db)) -> HRDashboardSummary:
    return HRService(db).dashboard(user)


@router.get("/employees", response_model=PaginatedResponse, dependencies=[Depends(require_permissions("hr.view"))])
def list_employees(
    q: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedResponse:
    items, total = HRService(db).list_employees(user, page=page, page_size=page_size, q=q, status=status)
    return PaginatedResponse(items=[HREmployeeRead.model_validate(serialize_employee(item)) for item in items], total=total, page=page, page_size=page_size)


@router.post("/employees", response_model=HREmployeeRead, dependencies=[Depends(require_permissions("hr.employee.manage"))])
def create_employee(payload: HREmployeeCreate, user=Depends(get_current_user), db: Session = Depends(get_db)) -> HREmployeeRead:
    employee = HRService(db).create_employee(payload, user)
    return HREmployeeRead.model_validate(serialize_employee(employee))


@router.put("/employees/{employee_id}", response_model=HREmployeeRead, dependencies=[Depends(require_permissions("hr.employee.manage"))])
def update_employee(employee_id: UUID, payload: HREmployeeCreate, user=Depends(get_current_user), db: Session = Depends(get_db)) -> HREmployeeRead:
    employee = HRService(db).update_employee(employee_id, payload, user)
    return HREmployeeRead.model_validate(serialize_employee(employee))


@router.get("/designations", response_model=list[HRDesignationRead], dependencies=[Depends(require_permissions("hr.view"))])
def list_designations(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[HRDesignationRead]:
    return [HRDesignationRead.model_validate(item) for item in HRService(db).list_designations(user)]


@router.post("/designations", response_model=HRDesignationRead, dependencies=[Depends(require_permissions("hr.employee.manage"))])
def create_designation(payload: HRDesignationCreate, user=Depends(get_current_user), db: Session = Depends(get_db)) -> HRDesignationRead:
    return HRDesignationRead.model_validate(HRService(db).create_designation(payload, user))


@router.get("/attendance", response_model=list[HRAttendanceRead], dependencies=[Depends(require_permissions("hr.attendance.manage"))])
def list_attendance(
    attendance_date: date | None = None,
    employee_id: UUID | None = None,
    status: str | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[HRAttendanceRead]:
    return [HRAttendanceRead.model_validate(serialize_attendance(item)) for item in HRService(db).list_attendance(user, attendance_date=attendance_date, employee_id=employee_id, status=status)]


@router.post("/attendance", response_model=HRAttendanceRead, dependencies=[Depends(require_permissions("hr.attendance.manage"))])
def mark_attendance(payload: HRAttendanceCreate, user=Depends(get_current_user), db: Session = Depends(get_db)) -> HRAttendanceRead:
    return HRAttendanceRead.model_validate(serialize_attendance(HRService(db).mark_attendance(payload, user)))


@router.get("/documents", response_model=list[HREmployeeDocumentRead], dependencies=[Depends(require_permissions("hr.view"))])
def list_documents(
    employee_id: UUID | None = None,
    status: str | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[HREmployeeDocumentRead]:
    return [HREmployeeDocumentRead.model_validate(serialize_document(item)) for item in HRService(db).list_documents(user, employee_id=employee_id, status=status)]


@router.post("/documents", response_model=HREmployeeDocumentRead, dependencies=[Depends(require_permissions("hr.documents.manage"))])
def create_document(payload: HREmployeeDocumentCreate, user=Depends(get_current_user), db: Session = Depends(get_db)) -> HREmployeeDocumentRead:
    return HREmployeeDocumentRead.model_validate(serialize_document(HRService(db).create_document(payload, user)))


@router.delete("/documents/{document_id}", dependencies=[Depends(require_permissions("hr.documents.manage"))])
def delete_document(document_id: UUID, user=Depends(get_current_user), db: Session = Depends(get_db)):
    HRService(db).delete_document(document_id, user)
    return {"success": True}


@router.get("/shifts", response_model=list[HRShiftRead], dependencies=[Depends(require_permissions("hr.shift.manage"))])
def list_shifts(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[HRShiftRead]:
    return [HRShiftRead.model_validate(item) for item in HRService(db).list_shifts(user)]


@router.post("/shifts", response_model=HRShiftRead, dependencies=[Depends(require_permissions("hr.shift.manage"))])
def create_shift(payload: HRShiftCreate, user=Depends(get_current_user), db: Session = Depends(get_db)) -> HRShiftRead:
    return HRShiftRead.model_validate(HRService(db).create_shift(payload, user))


@router.get("/roster", response_model=list[HRDutyRosterRead], dependencies=[Depends(require_permissions("hr.shift.manage"))])
def list_roster(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[HRDutyRosterRead]:
    return [HRDutyRosterRead.model_validate(serialize_roster(item)) for item in HRService(db).list_roster(user)]


@router.post("/roster", response_model=HRDutyRosterRead, dependencies=[Depends(require_permissions("hr.shift.manage"))])
def create_roster(payload: HRDutyRosterCreate, user=Depends(get_current_user), db: Session = Depends(get_db)) -> HRDutyRosterRead:
    return HRDutyRosterRead.model_validate(serialize_roster(HRService(db).create_roster(payload, user)))


@router.get("/leave-types", response_model=list[HRLeaveTypeRead], dependencies=[Depends(require_permissions("hr.leave.manage"))])
def list_leave_types(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[HRLeaveTypeRead]:
    return [HRLeaveTypeRead.model_validate(item) for item in HRService(db).list_leave_types(user)]


@router.post("/leave-types", response_model=HRLeaveTypeRead, dependencies=[Depends(require_permissions("hr.leave.manage"))])
def create_leave_type(payload: HRLeaveTypeCreate, user=Depends(get_current_user), db: Session = Depends(get_db)) -> HRLeaveTypeRead:
    return HRLeaveTypeRead.model_validate(HRService(db).create_leave_type(payload, user))


@router.get("/leave-requests", response_model=list[HRLeaveRequestRead], dependencies=[Depends(require_permissions("hr.leave.manage"))])
def list_leave_requests(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[HRLeaveRequestRead]:
    items = HRService(db).list_leave_requests(user)
    return [HRLeaveRequestRead.model_validate(serialize_leave(item)) for item in items]


@router.post("/leave-requests", response_model=HRLeaveRequestRead, dependencies=[Depends(require_permissions("hr.leave.manage"))])
def request_leave(payload: HRLeaveRequestCreate, user=Depends(get_current_user), db: Session = Depends(get_db)) -> HRLeaveRequestRead:
    item = HRService(db).request_leave(payload, user)
    return HRLeaveRequestRead.model_validate(serialize_leave(item))


@router.post("/leave-requests/{request_id}/approve", response_model=HRLeaveRequestRead, dependencies=[Depends(require_permissions("hr.leave.approve"))])
def approve_leave(request_id: UUID, remarks: str | None = None, user=Depends(get_current_user), db: Session = Depends(get_db)) -> HRLeaveRequestRead:
    item = HRService(db).decide_leave(request_id, user, status="approved", remarks=remarks)
    return HRLeaveRequestRead.model_validate(serialize_leave(item))


@router.post("/leave-requests/{request_id}/reject", response_model=HRLeaveRequestRead, dependencies=[Depends(require_permissions("hr.leave.approve"))])
def reject_leave(request_id: UUID, remarks: str | None = None, user=Depends(get_current_user), db: Session = Depends(get_db)) -> HRLeaveRequestRead:
    item = HRService(db).decide_leave(request_id, user, status="rejected", remarks=remarks)
    return HRLeaveRequestRead.model_validate(serialize_leave(item))


@router.post("/salary-structures", response_model=HRSalaryStructureRead, dependencies=[Depends(require_permissions("hr.payroll.manage"))])
def upsert_salary(payload: HRSalaryStructureCreate, user=Depends(get_current_user), db: Session = Depends(get_db)) -> HRSalaryStructureRead:
    return HRSalaryStructureRead.model_validate(_salary_payload(HRService(db).upsert_salary(payload, user)))


@router.get("/salary-structures", response_model=list[HRSalaryStructureRead], dependencies=[Depends(require_permissions("hr.payroll.manage"))])
def list_salary_structures(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[HRSalaryStructureRead]:
    return [HRSalaryStructureRead.model_validate(serialize_salary(item)) for item in HRService(db).list_salary_structures(user)]


@router.post("/overtime", dependencies=[Depends(require_permissions("hr.payroll.manage"))])
def create_overtime(payload: HROvertimeCreate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return _named_payload(HRService(db).create_overtime(payload, user))


@router.get("/overtime", response_model=list[HROvertimeRead], dependencies=[Depends(require_permissions("hr.payroll.manage"))])
def list_overtime(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[HROvertimeRead]:
    return [HROvertimeRead.model_validate(_named_payload(item)) for item in HRService(db).list_overtime(user)]


@router.post("/loans", dependencies=[Depends(require_permissions("hr.payroll.manage"))])
def create_loan(payload: HRLoanCreate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return _named_payload(HRService(db).create_loan(payload, user))


@router.get("/loans", response_model=list[HRLoanRead], dependencies=[Depends(require_permissions("hr.payroll.manage"))])
def list_loans(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[HRLoanRead]:
    return [HRLoanRead.model_validate(_named_payload(item)) for item in HRService(db).list_loans(user)]


@router.get("/payroll/dashboard", response_model=HRPayrollDashboard, dependencies=[Depends(require_permissions("payroll.view"))])
def payroll_dashboard(payroll_month: str | None = None, user=Depends(get_current_user), db: Session = Depends(get_db)) -> HRPayrollDashboard:
    return HRService(db).payroll_dashboard(user, payroll_month=payroll_month)


@router.get("/payroll/runs", response_model=list[HRPayrollRunRead], dependencies=[Depends(require_permissions("hr.payroll.manage"))])
def list_payroll_runs(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[HRPayrollRunRead]:
    return [HRPayrollRunRead.model_validate(_payroll_run_payload(item)) for item in HRService(db).list_payroll_runs(user)]


@router.post("/payroll/process", response_model=HRPayrollRunRead, dependencies=[Depends(require_permissions("hr.payroll.manage"))])
def process_payroll(payload: HRPayrollRunCreate, user=Depends(get_current_user), db: Session = Depends(get_db)) -> HRPayrollRunRead:
    return HRPayrollRunRead.model_validate(_payroll_run_payload(HRService(db).process_payroll(payload, user)))


@router.post("/payroll/runs/{run_id}/{status}", response_model=HRPayrollRunRead, dependencies=[Depends(require_permissions("hr.payroll.approve"))])
def decide_payroll(run_id: UUID, status: str, user=Depends(get_current_user), db: Session = Depends(get_db)) -> HRPayrollRunRead:
    return HRPayrollRunRead.model_validate(_payroll_run_payload(HRService(db).approve_payroll(run_id, user, status=status)))


@router.get("/reports/summary", response_model=HRReportSummary, dependencies=[Depends(require_permissions("hr.reports.view"))])
def report_summary(
    date_from: date | None = None,
    date_to: date | None = None,
    payroll_month: str | None = None,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HRReportSummary:
    return HRService(db).report_summary(user, date_from=date_from, date_to=date_to, payroll_month=payroll_month)


@router.post("/recruitment/jobs", dependencies=[Depends(require_permissions("hr.recruitment.manage"))])
def create_recruitment_job(payload: HRRecruitmentJobCreate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return HRService(db).create_recruitment_job(payload, user)


@router.post("/recruitment/candidates", dependencies=[Depends(require_permissions("hr.recruitment.manage"))])
def create_candidate(payload: HRCandidateCreate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return HRService(db).create_candidate(payload, user)


@router.post("/performance", dependencies=[Depends(require_permissions("hr.performance.manage"))])
def create_performance_review(payload: HRPerformanceCreate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return _named_payload(HRService(db).create_performance_review(payload, user))


@router.post("/resignations", dependencies=[Depends(require_permissions("hr.exit.manage"))])
def create_resignation(payload: HRResignationCreate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return _named_payload(HRService(db).create_resignation(payload, user))


@router.get("/settings", response_model=list[HRSettingRead], dependencies=[Depends(require_permissions("hr.settings.manage"))])
def list_settings(user=Depends(get_current_user), db: Session = Depends(get_db)) -> list[HRSettingRead]:
    return [HRSettingRead.model_validate(item) for item in HRService(db).list_settings(user)]


@router.put("/settings/{setting_key}", response_model=HRSettingRead, dependencies=[Depends(require_permissions("hr.settings.manage"))])
def update_setting(setting_key: str, payload: HRSettingUpdate, user=Depends(get_current_user), db: Session = Depends(get_db)) -> HRSettingRead:
    return HRSettingRead.model_validate(HRService(db).update_setting(setting_key, payload, user))
