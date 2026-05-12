export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface HRDashboardSummary {
  total_employees: number;
  active_employees: number;
  inactive_employees: number;
  new_joiners: number;
  resigned_staff: number;
  attendance: Record<string, number>;
  department_counts: Record<string, number>;
  category_counts: Record<string, number>;
  pending_leave_requests: number;
  pending_payroll_approvals: number;
  monthly_salary_payable: string | number;
  employees_on_leave: number;
  expiring_documents: number;
  current_month_payroll_status?: string | null;
  total_overtime_cost: string | number;
  total_deductions: string | number;
  alerts: string[];
}

export interface HREmployee {
  id: string;
  staff_code: string;
  full_name: string;
  phone?: string | null;
  email?: string | null;
  gender?: string | null;
  department_id?: string | null;
  designation_id?: string | null;
  department_name?: string | null;
  designation_name?: string | null;
  employee_type: string;
  employee_category: string;
  joining_date: string;
  employment_status: string;
  qualification?: string | null;
  specialization?: string | null;
  license_number?: string | null;
  license_expiry_date?: string | null;
  contract_end_date?: string | null;
  emergency_contact_name?: string | null;
  emergency_contact_phone?: string | null;
  bank_name?: string | null;
  bank_account_number?: string | null;
  salary_gross?: string | number | null;
  reporting_manager_name?: string | null;
  document_count: number;
  expiring_document_count: number;
}

export interface HREmployeeDocument {
  id: string;
  employee_id: string;
  employee_name?: string | null;
  staff_code?: string | null;
  document_type: string;
  file_name?: string | null;
  file_url?: string | null;
  expiry_date?: string | null;
  note?: string | null;
  status: string;
  days_to_expiry?: number | null;
  created_at: string;
}

export interface HRDesignation {
  id: string;
  department_id?: string | null;
  name: string;
  code?: string | null;
  grade?: string | null;
}

export interface HRAttendance {
  id: string;
  employee_id: string;
  employee_name?: string | null;
  staff_code?: string | null;
  attendance_date: string;
  status: string;
  check_in_at?: string | null;
  check_out_at?: string | null;
  working_hours: string | number;
  late_minutes: number;
  early_leave_minutes: number;
  note?: string | null;
}

export interface HRShift {
  id: string;
  name: string;
  code: string;
  shift_type: string;
  start_time: string;
  end_time: string;
  break_minutes: number;
  allowance_amount: string | number;
}

export interface HRRoster {
  id: string;
  employee_id: string;
  employee_name?: string | null;
  staff_code?: string | null;
  shift_id?: string | null;
  shift_name?: string | null;
  roster_date: string;
  duty_area?: string | null;
  duty_type: string;
  status: string;
}

export interface HRLeaveType {
  id: string;
  name: string;
  code: string;
  annual_quota: string | number;
  is_paid: boolean;
}

export interface HRLeaveRequest {
  id: string;
  employee_id: string;
  employee_name?: string | null;
  leave_type_id: string;
  leave_type_name?: string | null;
  start_date: string;
  end_date: string;
  number_of_days: string | number;
  status: string;
  reason?: string | null;
}

export interface HRPayrollItem {
  id: string;
  employee_id: string;
  employee_name?: string | null;
  staff_code?: string | null;
  payroll_month: string;
  present_days: string | number;
  absent_days: string | number;
  late_days: string | number;
  unpaid_leave_days: string | number;
  overtime_hours: string | number;
  gross_salary: string | number;
  basic_salary?: string | number | null;
  total_allowances?: string | number | null;
  overtime_amount?: string | number | null;
  loan_deduction?: string | number | null;
  attendance_deduction?: string | number | null;
  total_deductions: string | number;
  net_salary: string | number;
  payment_status: string;
  calculation_note?: string | null;
}

export interface HRPayrollRun {
  id: string;
  payroll_month: string;
  department_id?: string | null;
  status: string;
  total_employees: number;
  total_gross_salary: string | number;
  total_deductions: string | number;
  total_net_salary: string | number;
  created_at: string;
  items: HRPayrollItem[];
}

export interface HRPayrollDashboard {
  payroll_month: string;
  status?: string | null;
  total_salary_payable: string | number;
  pending_approvals: number;
  paid_items: number;
  unpaid_items: number;
  overtime_cost: string | number;
  deduction_total: string | number;
  department_costs: Record<string, string | number>;
}

export interface HRReportSummary {
  employee_count: number;
  attendance_summary: Record<string, number>;
  leave_summary: Record<string, number>;
  overtime_hours: string | number;
  payroll_net_total: string | number;
  loan_outstanding: string | number;
  expiring_documents: number;
  resigned_employees: number;
}

export interface HRSalaryStructure {
  id: string;
  employee_id: string;
  employee_name?: string | null;
  effective_from: string;
  basic_salary: string | number;
  gross_salary: string | number;
  total_deductions: string | number;
  net_salary: string | number;
}

export interface HRLoan {
  id: string;
  employee_id: string;
  employee_name?: string | null;
  loan_type: string;
  approved_amount: string | number;
  monthly_installment: string | number;
  deduction_start_month: string;
  remaining_balance: string | number;
  status: string;
}

export interface HROvertime {
  id: string;
  employee_id: string;
  employee_name?: string | null;
  overtime_date: string;
  overtime_hours: string | number;
  overtime_type: string;
  status: string;
  reason?: string | null;
}

export interface HRSetting {
  id: string;
  setting_key: string;
  setting_value?: string | null;
  description?: string | null;
}
