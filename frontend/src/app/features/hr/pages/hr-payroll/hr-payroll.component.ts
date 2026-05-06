import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';

import {
  HRAttendance,
  HRDashboardSummary,
  HREmployee,
  HRLeaveRequest,
  HRLeaveType,
  HRPayrollRun,
  HRRoster,
  HRSetting,
  HRShift,
} from '../../models/hr.models';
import { HRService } from '../../services/hr.service';

type HRTab = 'dashboard' | 'employees' | 'attendance' | 'roster' | 'leave' | 'payroll' | 'recruitment' | 'performance' | 'reports' | 'settings';

@Component({
  selector: 'app-hr-payroll',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './hr-payroll.component.html',
  styleUrls: ['./hr-payroll.component.scss'],
})
export class HRPayrollComponent {
  private readonly hrService = inject(HRService);
  private readonly route = inject(ActivatedRoute);

  readonly tab = signal<HRTab>('dashboard');

  loading = false;
  saving = false;
  error = '';
  success = '';
  query = '';
  employeeStatus = '';
  attendanceDate = this.today();

  summary: HRDashboardSummary | null = null;
  employees: HREmployee[] = [];
  attendance: HRAttendance[] = [];
  shifts: HRShift[] = [];
  roster: HRRoster[] = [];
  leaveTypes: HRLeaveType[] = [];
  leaveRequests: HRLeaveRequest[] = [];
  payrollRuns: HRPayrollRun[] = [];
  settings: HRSetting[] = [];

  selectedEmployee: HREmployee | null = null;
  selectedPayroll: HRPayrollRun | null = null;
  modal: '' | 'employee' | 'attendance' | 'shift' | 'roster' | 'leave' | 'salary' | 'payroll' | 'job' | 'candidate' | 'performance' | 'resignation' | 'setting' = '';

  employeeForm: Partial<HREmployee> = this.blankEmployee();
  attendanceForm: Record<string, unknown> = {};
  shiftForm: Record<string, unknown> = {};
  rosterForm: Record<string, unknown> = {};
  leaveForm: Record<string, unknown> = {};
  salaryForm: Record<string, unknown> = {};
  payrollForm = { payroll_month: this.currentMonth(), department_id: null as string | null, note: '' };
  jobForm: Record<string, unknown> = {};
  candidateForm: Record<string, unknown> = {};
  performanceForm: Record<string, unknown> = {};
  resignationForm: Record<string, unknown> = {};
  settingForm: Partial<HRSetting> = {};

  filteredEmployees(): HREmployee[] {
    const q = this.query.trim().toLowerCase();
    const rows = this.employees.filter((employee) => {
      const statusMatch = !this.employeeStatus || employee.employment_status === this.employeeStatus;
      const text = `${employee.staff_code} ${employee.full_name} ${employee.phone ?? ''} ${employee.email ?? ''} ${employee.department_name ?? ''} ${employee.employee_category}`.toLowerCase();
      return statusMatch && (!q || text.includes(q));
    });
    return rows.sort((a, b) => a.full_name.localeCompare(b.full_name));
  }

  constructor() {
    this.route.data.subscribe((data) => {
      this.tab.set((data['hrTab'] as HRTab) || 'dashboard');
      this.loadCurrentTab();
    });
  }

  loadCurrentTab(): void {
    this.error = '';
    this.loadBase();
    if (this.tab() === 'dashboard') this.loadDashboard();
    if (this.tab() === 'attendance') this.loadAttendance();
    if (this.tab() === 'roster') this.loadRoster();
    if (this.tab() === 'leave') this.loadLeave();
    if (this.tab() === 'payroll') this.loadPayroll();
    if (this.tab() === 'settings') this.loadSettings();
  }

  loadBase(): void {
    this.hrService.listEmployees({ page_size: 500 }).subscribe({
      next: (response) => (this.employees = response.items),
      error: (error) => this.showError(error),
    });
    this.hrService.listShifts().subscribe((rows) => (this.shifts = rows));
    this.hrService.listLeaveTypes().subscribe((rows) => (this.leaveTypes = rows));
  }

  loadDashboard(): void {
    this.hrService.dashboard().subscribe({ next: (summary) => (this.summary = summary), error: (error) => this.showError(error) });
  }

  loadAttendance(): void {
    this.hrService.listAttendance(this.attendanceDate).subscribe({ next: (rows) => (this.attendance = rows), error: (error) => this.showError(error) });
  }

  loadRoster(): void {
    this.hrService.listRoster().subscribe({ next: (rows) => (this.roster = rows), error: (error) => this.showError(error) });
  }

  loadLeave(): void {
    this.hrService.listLeaveRequests().subscribe({ next: (rows) => (this.leaveRequests = rows), error: (error) => this.showError(error) });
  }

  loadPayroll(): void {
    this.hrService.listPayrollRuns().subscribe({ next: (rows) => (this.payrollRuns = rows), error: (error) => this.showError(error) });
  }

  loadSettings(): void {
    this.hrService.listSettings().subscribe({ next: (rows) => (this.settings = rows), error: (error) => this.showError(error) });
  }

  openModal(name: typeof this.modal, employee?: HREmployee, setting?: HRSetting): void {
    this.error = '';
    this.success = '';
    this.modal = name;
    this.selectedEmployee = employee ?? null;
    if (name === 'employee') this.employeeForm = employee ? { ...employee } : this.blankEmployee();
    if (name === 'attendance') this.attendanceForm = { employee_id: employee?.id ?? '', attendance_date: this.today(), status: 'present', working_hours: 8, late_minutes: 0, early_leave_minutes: 0 };
    if (name === 'shift') this.shiftForm = { name: '', code: '', shift_type: 'morning', start_time: '08:00', end_time: '14:00', break_minutes: 30, allowance_amount: 0 };
    if (name === 'roster') this.rosterForm = { employee_id: employee?.id ?? '', shift_id: this.shifts[0]?.id ?? '', roster_date: this.today(), duty_area: 'General Ward', duty_type: 'regular', status: 'assigned' };
    if (name === 'leave') this.leaveForm = { employee_id: employee?.id ?? '', leave_type_id: this.leaveTypes[0]?.id ?? '', start_date: this.today(), end_date: this.today(), number_of_days: 1, reason: '' };
    if (name === 'salary') this.salaryForm = { employee_id: employee?.id ?? '', effective_from: this.today(), basic_salary: 30000, house_rent_allowance: 15000, medical_allowance: 3000, transport_allowance: 2000, food_allowance: 1500, night_duty_allowance: 0, on_call_allowance: 0, emergency_duty_allowance: 0, overtime_hourly_rate: 250, bonus_incentive: 0, tax_deduction: 0, provident_fund_deduction: 1500, other_deductions: 0 };
    if (name === 'payroll') this.payrollForm = { payroll_month: this.currentMonth(), department_id: null, note: 'Monthly payroll preview' };
    if (name === 'job') this.jobForm = { title: '', number_of_positions: 1, status: 'open', closing_date: this.today(), salary_range: '', description: '' };
    if (name === 'candidate') this.candidateForm = { full_name: '', phone: '', email: '', status: 'applied', notes: '' };
    if (name === 'performance') this.performanceForm = { employee_id: employee?.id ?? '', review_period: this.currentMonth(), rating: 4, feedback: '', kpi_summary: '', recommendation: '' };
    if (name === 'resignation') this.resignationForm = { employee_id: employee?.id ?? '', resignation_date: this.today(), last_working_date: this.today(), reason: '' };
    if (name === 'setting') this.settingForm = setting ? { ...setting } : {};
  }

  closeModal(): void {
    this.modal = '';
  }

  saveEmployee(): void {
    const payload = { ...this.employeeForm, joining_date: this.employeeForm.joining_date || this.today(), employee_type: this.employeeForm.employee_type || 'full_time', employee_category: this.employeeForm.employee_category || 'other', employment_status: this.employeeForm.employment_status || 'active' };
    this.submit(this.selectedEmployee ? this.hrService.updateEmployee(this.selectedEmployee.id, payload) : this.hrService.createEmployee(payload), 'Employee saved');
  }

  saveAttendance(): void {
    this.submit(this.hrService.markAttendance(this.attendanceForm), 'Attendance saved');
  }

  saveShift(): void {
    this.submit(this.hrService.createShift(this.shiftForm), 'Shift created');
  }

  saveRoster(): void {
    this.submit(this.hrService.createRoster(this.rosterForm), 'Roster assigned');
  }

  saveLeave(): void {
    this.submit(this.hrService.requestLeave(this.leaveForm), 'Leave request saved');
  }

  decideLeave(request: HRLeaveRequest, action: 'approve' | 'reject'): void {
    this.submit(this.hrService.decideLeave(request.id, action), `Leave ${action}d`);
  }

  saveSalary(): void {
    this.submit(this.hrService.upsertSalary(this.salaryForm), 'Salary structure saved');
  }

  savePayroll(): void {
    this.submit(this.hrService.processPayroll(this.payrollForm), 'Payroll preview generated');
  }

  decidePayroll(run: HRPayrollRun, status: string): void {
    this.submit(this.hrService.decidePayroll(run.id, status), `Payroll marked ${status}`);
  }

  saveJob(): void {
    this.submit(this.hrService.createRecruitmentJob(this.jobForm), 'Job opening saved');
  }

  saveCandidate(): void {
    this.submit(this.hrService.createCandidate(this.candidateForm), 'Candidate saved');
  }

  savePerformance(): void {
    this.submit(this.hrService.createPerformance(this.performanceForm), 'Performance note saved');
  }

  saveResignation(): void {
    this.submit(this.hrService.createResignation(this.resignationForm), 'Exit workflow started');
  }

  saveSetting(): void {
    if (!this.settingForm.setting_key) return;
    this.submit(this.hrService.updateSetting(this.settingForm.setting_key, this.settingForm), 'Setting updated');
  }

  viewPayslip(run: HRPayrollRun): void {
    this.selectedPayroll = run;
  }

  printPayslip(): void {
    window.print();
  }

  exportEmployees(): void {
    const rows = this.filteredEmployees().map((employee) => [employee.staff_code, employee.full_name, employee.department_name || '', employee.employee_category, employee.phone || '', employee.employment_status].join(','));
    const blob = new Blob([['Staff Code,Name,Department,Category,Phone,Status', ...rows].join('\n')], { type: 'text/csv;charset=utf-8' });
    const anchor = document.createElement('a');
    anchor.href = URL.createObjectURL(blob);
    anchor.download = 'hr-employees.csv';
    anchor.click();
    URL.revokeObjectURL(anchor.href);
  }

  formatMoney(value: string | number | null | undefined): string {
    return new Intl.NumberFormat('en-BD', { style: 'currency', currency: 'BDT', minimumFractionDigits: 0 }).format(Number(value ?? 0));
  }

  statusClass(status: string | undefined | null): string {
    return `status status-${(status || 'neutral').replace('_', '-')}`;
  }

  attendanceTotal(status: string): number {
    return this.attendance.filter((item) => item.status === status).length;
  }

  private submit<T>(request$: import('rxjs').Observable<T>, message: string): void {
    this.saving = true;
    this.error = '';
    request$.subscribe({
      next: () => {
        this.saving = false;
        this.success = message;
        this.closeModal();
        this.loadCurrentTab();
      },
      error: (error) => {
        this.saving = false;
        this.showError(error);
      },
    });
  }

  private showError(error: unknown): void {
    const anyError = error as { error?: { message?: string; detail?: string }; message?: string };
    this.error = anyError.error?.message || anyError.error?.detail || anyError.message || 'Could not complete the HR action.';
  }

  private blankEmployee(): Partial<HREmployee> {
    return { full_name: '', phone: '', email: '', gender: 'female', employee_type: 'full_time', employee_category: 'nurse', joining_date: this.today(), employment_status: 'active' };
  }

  private today(): string {
    return new Date().toISOString().slice(0, 10);
  }

  private currentMonth(): string {
    return new Date().toISOString().slice(0, 7);
  }
}
