import { CommonModule, KeyValue } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';

import { PERMISSIONS } from '../../../../core/constants/permissions';
import { NotificationService } from '../../../../core/services/notification.service';
import { SessionService } from '../../../../core/services/session.service';
import { HREmployee } from '../../../hr/models/hr.models';
import { HRService } from '../../../hr/services/hr.service';
import { Patient } from '../../../patients/models/patient.models';
import { PatientService } from '../../../patients/services/patient.service';
import {
  TransportDashboard,
  TransportDriver,
  TransportFuelLog,
  TransportMaintenance,
  TransportReport,
  TransportRequest,
  TransportSchedule,
  TransportSetting,
  TransportTrip,
  TransportVehicle,
} from '../../models/transport.models';
import { TransportService } from '../../services/transport.service';

type TransportTab = 'dashboard' | 'requests' | 'dispatch' | 'trips' | 'vehicles' | 'drivers' | 'schedule' | 'maintenance' | 'fuel' | 'reports' | 'settings';

@Component({
  selector: 'app-transport-workspace',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './transport-workspace.component.html',
  styleUrls: ['./transport-workspace.component.scss'],
})
export class TransportWorkspaceComponent {
  private readonly transport = inject(TransportService);
  private readonly patientsService = inject(PatientService);
  private readonly hrService = inject(HRService);
  private readonly route = inject(ActivatedRoute);
  private readonly notifications = inject(NotificationService);
  readonly session = inject(SessionService);
  readonly permissions = PERMISSIONS;

  readonly tab = signal<TransportTab>('dashboard');
  today = new Date().toISOString().slice(0, 10);
  filters = { vehicle_type: '', status: '', driver_id: '', department: '', trip_type: '', date: this.today, priority: '' };
  reportFilters = { report_type: 'trip_history', status: '', trip_type: '', vehicle_id: '', driver_id: '' };

  dashboard: TransportDashboard | null = null;
  vehicles: TransportVehicle[] = [];
  drivers: TransportDriver[] = [];
  requests: TransportRequest[] = [];
  trips: TransportTrip[] = [];
  schedules: TransportSchedule[] = [];
  maintenance: TransportMaintenance[] = [];
  fuelLogs: TransportFuelLog[] = [];
  settings: TransportSetting[] = [];
  patients: Patient[] = [];
  employees: HREmployee[] = [];
  report: TransportReport | null = null;
  modal: '' | 'request' | 'vehicle' | 'driver' | 'dispatch' | 'schedule' | 'maintenance' | 'fuel' | 'setting' = '';
  selectedRequest: TransportRequest | null = null;
  error = '';
  success = '';

  requestForm: Record<string, unknown> = {};
  vehicleForm: Record<string, unknown> = {};
  driverForm: Record<string, unknown> = {};
  dispatchForm: Record<string, unknown> = {};
  scheduleForm: Record<string, unknown> = {};
  maintenanceForm: Record<string, unknown> = {};
  fuelForm: Record<string, unknown> = {};
  settingForm: Record<string, unknown> = {};

  readonly vehicleTypes = ['ambulance', 'icu_ambulance', 'basic_life_support_ambulance', 'advanced_life_support_ambulance', 'patient_transport_van', 'staff_transport_vehicle', 'supply_vehicle', 'utility_vehicle', 'other'];
  readonly equipment = ['oxygen_cylinder', 'stretcher', 'wheelchair', 'monitor', 'defibrillator', 'suction_machine', 'emergency_kit', 'iv_stand'];
  readonly statuses = ['requested', 'pending_assignment', 'vehicle_assigned', 'driver_assigned', 'dispatched', 'arrived_at_pickup', 'patient_picked_up', 'in_transit', 'arrived_at_destination', 'completed', 'cancelled', 'delayed'];
  readonly tabs: TransportTab[] = ['dashboard', 'requests', 'dispatch', 'trips', 'vehicles', 'drivers', 'schedule', 'maintenance', 'fuel', 'reports', 'settings'];

  constructor() {
    this.route.data.subscribe((data) => {
      this.tab.set((data['transportTab'] as TransportTab) || 'dashboard');
      this.loadCurrentTab();
    });
    this.loadReferenceData();
  }

  loadReferenceData(): void {
    this.transport.listVehicles().subscribe((rows) => (this.vehicles = rows));
    this.transport.listDrivers().subscribe((rows) => (this.drivers = rows));
    this.patientsService.list().subscribe((rows) => (this.patients = rows));
    this.hrService.listEmployees({ page_size: 500 }).subscribe((response) => (this.employees = response.items));
  }

  loadCurrentTab(): void {
    this.error = '';
    this.loadDashboard();
    if (this.tab() === 'requests' || this.tab() === 'dispatch') this.loadRequests();
    if (this.tab() === 'trips' || this.tab() === 'dispatch') this.loadTrips();
    if (this.tab() === 'vehicles') this.loadVehicles();
    if (this.tab() === 'drivers') this.loadDrivers();
    if (this.tab() === 'schedule') this.loadSchedules();
    if (this.tab() === 'maintenance') this.loadMaintenance();
    if (this.tab() === 'fuel') this.loadFuel();
    if (this.tab() === 'reports') this.loadReport();
    if (this.tab() === 'settings') this.loadSettings();
  }

  loadDashboard(): void {
    this.transport.dashboard(this.filters).subscribe({ next: (row) => (this.dashboard = row), error: (error) => this.showError(error) });
  }

  loadVehicles(): void {
    this.transport.listVehicles({ vehicle_type: this.filters.vehicle_type, status: this.filters.status }).subscribe({ next: (rows) => (this.vehicles = rows), error: (error) => this.showError(error) });
  }

  loadDrivers(): void {
    this.transport.listDrivers({ status: this.filters.status }).subscribe({ next: (rows) => (this.drivers = rows), error: (error) => this.showError(error) });
  }

  loadRequests(): void {
    this.transport.listRequests({ status: this.filters.status, priority: this.filters.priority, trip_type: this.filters.trip_type, department: this.filters.department }).subscribe({ next: (rows) => (this.requests = rows), error: (error) => this.showError(error) });
  }

  loadTrips(): void {
    this.transport.listTrips({ status: this.filters.status, trip_type: this.filters.trip_type, driver_id: this.filters.driver_id }).subscribe({ next: (rows) => (this.trips = rows), error: (error) => this.showError(error) });
  }

  loadSchedules(): void {
    this.transport.listSchedules().subscribe({ next: (rows) => (this.schedules = rows), error: (error) => this.showError(error) });
  }

  loadMaintenance(): void {
    this.transport.listMaintenance().subscribe({ next: (rows) => (this.maintenance = rows), error: (error) => this.showError(error) });
  }

  loadFuel(): void {
    this.transport.listFuelLogs().subscribe({ next: (rows) => (this.fuelLogs = rows), error: (error) => this.showError(error) });
  }

  loadSettings(): void {
    this.transport.listSettings().subscribe({ next: (rows) => (this.settings = rows), error: (error) => this.showError(error) });
  }

  loadReport(): void {
    this.transport.report(this.reportFilters).subscribe({ next: (report) => (this.report = report), error: (error) => this.showError(error) });
  }

  openModal(name: typeof this.modal, request?: TransportRequest): void {
    this.modal = name;
    this.selectedRequest = request || null;
    this.error = '';
    this.success = '';
    if (name === 'request') this.requestForm = { request_type: 'Emergency', trip_type: 'home_to_hospital', source_department: 'Emergency', patient_id: '', staff_employee_id: '', unknown_patient_name: '', pickup_location: '', dropoff_location: 'Hospital Emergency', required_at: this.localDateTime(), urgency: 'routine', priority: 'normal', required_vehicle_type: 'ambulance', required_equipment: [], attendant_required: false, billing_required: false, reason: '' };
    if (name === 'vehicle') this.vehicleForm = { vehicle_number: '', registration_number: '', vehicle_type: 'ambulance', capacity: 1, equipment_available: [...this.equipment.slice(0, 3)], fuel_type: 'diesel', current_status: 'available', remarks: '' };
    if (name === 'driver') this.driverForm = { employee_id: '', driver_name: '', contact_number: '', license_number: '', license_expiry_date: '', assigned_vehicle_id: '', shift: 'day', availability_status: 'available', emergency_contact: '' };
    if (name === 'dispatch') this.dispatchForm = { vehicle_id: this.availableVehicles()[0]?.id || '', driver_id: this.availableDrivers()[0]?.id || '', scheduled_at: this.localDateTime(), override: false, override_reason: '', remarks: '' };
    if (name === 'schedule') this.scheduleForm = { vehicle_id: '', driver_id: '', schedule_type: 'booking', start_at: this.localDateTime(), end_at: this.localDateTime(60), recurrence_rule: '', status: 'scheduled', purpose: '' };
    if (name === 'maintenance') this.maintenanceForm = { vehicle_id: this.vehicles[0]?.id || '', maintenance_type: 'service', service_date: this.today, odometer_reading: 0, workshop_vendor: '', cost: 0, next_service_date: '', parts_changed: '', status: 'completed' };
    if (name === 'fuel') this.fuelForm = { vehicle_id: this.vehicles[0]?.id || '', fuel_date: this.today, quantity: 0, fuel_cost: 0, odometer_reading: 0, filled_by: '', expense_category: 'fuel', remarks: '' };
    if (name === 'setting') this.settingForm = { setting_key: '', setting_value: '', description: '' };
  }

  closeModal(): void {
    this.modal = '';
  }

  saveRequest(emergency = false): void {
    this.submit(this.transport.createRequest(this.clean(this.requestForm), emergency), emergency ? 'Emergency request created' : 'Transport request created');
  }

  saveVehicle(): void {
    this.submit(this.transport.saveVehicle(this.clean(this.vehicleForm)), 'Vehicle saved');
  }

  saveDriver(): void {
    const payload = this.clean(this.driverForm);
    const employee = this.employees.find((item) => item.id === payload['employee_id']);
    if (employee && !payload['driver_name']) {
      payload['driver_name'] = employee.full_name;
      payload['contact_number'] = employee.phone || null;
      payload['license_number'] = employee.license_number || payload['license_number'];
    }
    this.submit(this.transport.saveDriver(payload), 'Driver saved');
  }

  dispatch(): void {
    if (!this.selectedRequest) return;
    this.submit(this.transport.dispatch(this.selectedRequest.id, this.clean(this.dispatchForm)), 'Trip dispatched');
  }

  setTripStatus(trip: TransportTrip, status: string): void {
    const payload: Record<string, unknown> = { status };
    if (status === 'completed') {
      payload['distance_km'] = Number(window.prompt('Distance km', String(trip.distance_km || 0)) || 0);
      payload['waiting_minutes'] = Number(window.prompt('Waiting minutes', String(trip.waiting_minutes || 0)) || 0);
    }
    this.submit(this.transport.updateTripStatus(trip.id, payload), 'Trip status updated');
  }

  saveSchedule(): void {
    this.submit(this.transport.createSchedule(this.clean(this.scheduleForm)), 'Schedule saved');
  }

  saveMaintenance(): void {
    this.submit(this.transport.createMaintenance(this.clean(this.maintenanceForm)), 'Maintenance record saved');
  }

  saveFuel(): void {
    this.submit(this.transport.createFuelLog(this.clean(this.fuelForm)), 'Fuel or expense recorded');
  }

  saveSetting(): void {
    this.submit(this.transport.upsertSetting(this.clean(this.settingForm)), 'Setting saved');
  }

  toggleVehicleEquipment(item: string, checked: boolean): void {
    const current = new Set((this.vehicleForm['equipment_available'] as string[]) || []);
    checked ? current.add(item) : current.delete(item);
    this.vehicleForm['equipment_available'] = Array.from(current);
  }

  hasVehicleEquipment(item: string): boolean {
    return ((this.vehicleForm['equipment_available'] as string[]) || []).includes(item);
  }

  availableVehicles(): TransportVehicle[] {
    return this.vehicles.filter((item) => ['available', 'reserved'].includes(item.current_status) && item.readiness_status !== 'not_ready');
  }

  availableDrivers(): TransportDriver[] {
    return this.drivers.filter((item) => ['available', 'assigned'].includes(item.availability_status));
  }

  statusClass(status: string | null | undefined): string {
    return `status-chip ${(status || 'neutral').replaceAll('-', '_')}`;
  }

  formatMoney(value: string | number | null | undefined): string {
    return new Intl.NumberFormat('en-BD', { style: 'currency', currency: 'BDT', maximumFractionDigits: 0 }).format(Number(value || 0));
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
        this.notifications.success(message);
      },
      error: (error) => this.showError(error),
    });
  }

  private clean(source: Record<string, unknown>): Record<string, unknown> {
    return Object.fromEntries(Object.entries(source).map(([key, value]) => [key, Array.isArray(value) ? value : value === '' ? null : value]));
  }

  private showError(error: unknown): void {
    const anyError = error as { error?: { message?: string; detail?: string }; message?: string };
    this.error = anyError.error?.message || anyError.error?.detail || anyError.message || 'Could not complete transport action.';
  }

  private localDateTime(addMinutes = 0): string {
    const now = new Date(Date.now() + addMinutes * 60000);
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    return now.toISOString().slice(0, 16);
  }
}
