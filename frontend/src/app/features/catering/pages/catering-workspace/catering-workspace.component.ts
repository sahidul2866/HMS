import { CommonModule, KeyValue } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { NotificationService } from '../../../../core/services/notification.service';
import { Patient } from '../../../patients/models/patient.models';
import { PatientService } from '../../../patients/services/patient.service';
import { HREmployee } from '../../../hr/models/hr.models';
import { HRService } from '../../../hr/services/hr.service';
import {
  CateringDashboard,
  CateringDietOrder,
  CateringDietType,
  CateringMealPlan,
  CateringMealSchedule,
  CateringMealTask,
  CateringReport,
  CateringSetting,
  CateringStaffMeal,
} from '../../models/catering.models';
import { CateringService } from '../../services/catering.service';

type CateringTab = 'dashboard' | 'diet-orders' | 'kitchen' | 'schedule' | 'delivery' | 'staff-meals' | 'inventory' | 'reports' | 'settings';

@Component({
  selector: 'app-catering-workspace',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './catering-workspace.component.html',
  styleUrls: ['./catering-workspace.component.scss'],
})
export class CateringWorkspaceComponent {
  private readonly cateringService = inject(CateringService);
  private readonly patientService = inject(PatientService);
  private readonly hrService = inject(HRService);
  private readonly route = inject(ActivatedRoute);
  private readonly notifications = inject(NotificationService);

  readonly tab = signal<CateringTab>('dashboard');
  today = new Date().toISOString().slice(0, 10);
  filters = { meal_date: this.today, meal_type: '', ward: '', bed: '', diet_type: '', kitchen_status: '', delivery_status: '' };
  reportFilters = { report_type: 'daily', meal_date: this.today, ward: '', diet_type: '', meal_type: '', kitchen_status: '', delivery_status: '' };

  dashboard: CateringDashboard | null = null;
  dietTypes: CateringDietType[] = [];
  mealPlans: CateringMealPlan[] = [];
  schedules: CateringMealSchedule[] = [];
  dietOrders: CateringDietOrder[] = [];
  meals: CateringMealTask[] = [];
  staffMeals: CateringStaffMeal[] = [];
  settings: CateringSetting[] = [];
  patients: Patient[] = [];
  employees: HREmployee[] = [];
  report: CateringReport | null = null;
  error = '';
  success = '';
  modal: '' | 'diet-order' | 'meal-plan' | 'diet-type' | 'schedule' | 'staff-meal' | 'setting' = '';

  dietOrderForm: Record<string, unknown> = {};
  mealPlanForm: Record<string, unknown> = {};
  dietTypeForm: Record<string, unknown> = {};
  scheduleForm: Record<string, unknown> = {};
  staffMealForm: Record<string, unknown> = {};
  settingForm: Record<string, unknown> = {};

  constructor() {
    this.route.data.subscribe((data) => {
      this.tab.set((data['cateringTab'] as CateringTab) || 'dashboard');
      this.loadCurrentTab();
    });
    this.loadReferenceData();
  }

  loadReferenceData(): void {
    this.cateringService.listDietTypes().subscribe((rows) => (this.dietTypes = rows));
    this.cateringService.listMealPlans().subscribe((rows) => (this.mealPlans = rows));
    this.cateringService.listSchedules().subscribe((rows) => (this.schedules = rows));
    this.patientService.list().subscribe((rows) => (this.patients = rows));
    this.hrService.listEmployees({ page_size: 500 }).subscribe((response) => (this.employees = response.items));
  }

  loadCurrentTab(): void {
    this.error = '';
    this.loadDashboard();
    if (this.tab() === 'diet-orders') this.loadDietOrders();
    if (this.tab() === 'kitchen' || this.tab() === 'delivery' || this.tab() === 'inventory') this.loadMeals();
    if (this.tab() === 'schedule') this.loadSchedule();
    if (this.tab() === 'staff-meals') this.loadStaffMeals();
    if (this.tab() === 'settings') this.loadSettings();
    if (this.tab() === 'reports') this.loadReport();
  }

  loadDashboard(): void {
    this.cateringService.dashboard(this.filters).subscribe({ next: (row) => (this.dashboard = row), error: (error) => this.showError(error) });
  }

  loadDietOrders(): void {
    this.cateringService.listDietOrders().subscribe({ next: (rows) => (this.dietOrders = rows), error: (error) => this.showError(error) });
  }

  loadMeals(): void {
    this.cateringService.listMeals(this.filters).subscribe({ next: (rows) => (this.meals = rows), error: (error) => this.showError(error) });
  }

  loadSchedule(): void {
    this.cateringService.listSchedules().subscribe((rows) => (this.schedules = rows));
    this.cateringService.listMealPlans().subscribe((rows) => (this.mealPlans = rows));
  }

  loadStaffMeals(): void {
    this.cateringService.listStaffMeals(this.filters.meal_date).subscribe({ next: (rows) => (this.staffMeals = rows), error: (error) => this.showError(error) });
  }

  loadSettings(): void {
    this.cateringService.listSettings().subscribe({ next: (rows) => (this.settings = rows), error: (error) => this.showError(error) });
  }

  loadReport(): void {
    this.cateringService.report(this.reportFilters).subscribe({ next: (report) => (this.report = report), error: (error) => this.showError(error) });
  }

  openModal(name: typeof this.modal): void {
    this.modal = name;
    this.error = '';
    this.success = '';
    if (name === 'diet-order') {
      this.dietOrderForm = { patient_id: this.patients[0]?.id || '', diet_type_id: this.dietTypes[0]?.id || '', meal_plan_id: '', ward_name: '', bed_number: '', admission_number: '', restrictions: '', allergies: '', special_instructions: '', nutrition_notes: '', start_at: this.localDateTime(), end_at: '' };
    }
    if (name === 'meal-plan') this.mealPlanForm = { diet_type_id: this.dietTypes[0]?.id || '', name: '', meal_type: 'lunch', ingredients: '', allergens: '', billable_amount: 0, inventory_quantity: 0 };
    if (name === 'diet-type') this.dietTypeForm = { code: '', name: '', description: '', is_npo: false, requires_approval: false, default_restrictions: '' };
    if (name === 'schedule') this.scheduleForm = { meal_type: 'custom', display_name: '', serving_time: '12:00', cutoff_minutes: 60, sort_order: this.schedules.length + 1 };
    if (name === 'staff-meal') this.staffMealForm = { employee_id: '', staff_name: '', staff_code: '', meal_date: this.today, meal_type: 'lunch', eligibility_type: 'paid', amount: 0, payroll_deductible: false, remarks: '' };
    if (name === 'setting') this.settingForm = { setting_key: '', setting_value: '', description: '' };
  }

  closeModal(): void {
    this.modal = '';
  }

  saveDietOrder(): void {
    this.submit(this.cateringService.createDietOrder(this.clean(this.dietOrderForm)), 'Diet order saved');
  }

  approveDietOrder(order: CateringDietOrder): void {
    this.submit(this.cateringService.approveDietOrder(order.id), 'Diet order approved');
  }

  saveMealPlan(): void {
    this.submit(this.cateringService.createMealPlan(this.clean(this.mealPlanForm)), 'Meal plan saved');
  }

  saveDietType(): void {
    this.submit(this.cateringService.createDietType(this.clean(this.dietTypeForm)), 'Diet type saved');
  }

  saveSchedule(): void {
    this.submit(this.cateringService.upsertSchedule(this.clean(this.scheduleForm)), 'Meal schedule saved');
  }

  generateMeals(): void {
    this.submit(this.cateringService.generateMeals(this.filters.meal_date), 'Daily meal tasks generated');
  }

  setMealStatus(task: CateringMealTask, preparationStatus?: string, deliveryStatus?: string): void {
    const payload: Record<string, unknown> = {};
    if (preparationStatus) payload['preparation_status'] = preparationStatus;
    if (deliveryStatus) payload['delivery_status'] = deliveryStatus;
    if (task.safety_warnings.length && ['preparing', 'ready'].includes(preparationStatus || '')) {
      const reason = window.prompt('Safety warning override reason');
      if (!reason) return;
      payload['override_reason'] = reason;
    }
    if (deliveryStatus === 'delivered') {
      payload['patient_response'] = 'accepted';
      payload['received_by'] = task.patient_name || 'Patient/Nurse';
    }
    if (deliveryStatus === 'refused') {
      const reason = window.prompt('Refusal reason');
      if (!reason) return;
      payload['patient_response'] = 'refused';
      payload['refusal_reason'] = reason;
    }
    this.submit(this.cateringService.updateMealStatus(task.id, payload), 'Meal status updated');
  }

  saveStaffMeal(): void {
    const payload = this.clean(this.staffMealForm);
    const employee = this.employees.find((item) => item.id === payload['employee_id']);
    if (employee) {
      payload['staff_name'] = employee.full_name;
      payload['staff_code'] = employee.staff_code;
      payload['department_id'] = employee.department_id || null;
    }
    this.submit(this.cateringService.createStaffMeal(payload), 'Staff meal saved');
  }

  updateStaffMealStatus(item: CateringStaffMeal, status: string): void {
    this.submit(this.cateringService.updateStaffMealStatus(item.id, status), `Staff meal ${status}`);
  }

  saveSetting(): void {
    this.submit(this.cateringService.upsertSetting(this.clean(this.settingForm)), 'Setting saved');
  }

  dashboardDrill(target: CateringTab, filter?: Partial<typeof this.filters>): void {
    this.filters = { ...this.filters, ...filter };
    this.tab.set(target);
    this.loadCurrentTab();
  }

  statusClass(status: string | null | undefined): string {
    return `status status-${(status || 'neutral').replaceAll('_', '-')}`;
  }

  formatMoney(value: string | number | null | undefined): string {
    return new Intl.NumberFormat('en-BD', { style: 'currency', currency: 'BDT', maximumFractionDigits: 0 }).format(Number(value || 0));
  }

  formatReportMoney(value: unknown): string {
    return this.formatMoney(typeof value === 'string' || typeof value === 'number' ? value : 0);
  }

  rowValue(row: Record<string, unknown>, key: string): string {
    const value = row[key];
    return value === null || value === undefined ? '-' : String(value);
  }

  sortKeyValue(a: KeyValue<string, number>, b: KeyValue<string, number>): number {
    return b.value - a.value;
  }

  private submit<T>(request$: import('rxjs').Observable<T>, message: string): void {
    request$.subscribe({
      next: () => {
        this.success = message;
        this.closeModal();
        this.loadReferenceData();
        this.loadCurrentTab();
      },
      error: (error) => this.showError(error),
    });
  }

  private clean(source: Record<string, unknown>): Record<string, unknown> {
    return Object.fromEntries(Object.entries(source).map(([key, value]) => [key, value === '' ? null : value]));
  }

  private showError(error: unknown): void {
    const anyError = error as { error?: { message?: string; detail?: string }; message?: string };
    this.error = anyError.error?.message || anyError.error?.detail || anyError.message || 'Could not complete catering action.';
  }

  private localDateTime(): string {
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    return now.toISOString().slice(0, 16);
  }
}
