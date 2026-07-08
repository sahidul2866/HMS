import { CommonModule, KeyValue } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';

import { PERMISSIONS } from '../../../../core/constants/permissions';
import { DoctorDirectoryService } from '../../../../core/services/doctor-directory.service';
import { NotificationService } from '../../../../core/services/notification.service';
import { SessionService } from '../../../../core/services/session.service';
import { User } from '../../../../core/models/auth.models';
import { Patient } from '../../../patients/models/patient.models';
import { PatientService } from '../../../patients/services/patient.service';
import { TelemedicineAppointment, TelemedicineChatMessage, TelemedicineConsultation, TelemedicineDashboard, TelemedicineFile, TelemedicineReport, TelemedicineSetting } from '../../models/telemedicine.models';
import { TelemedicineService } from '../../services/telemedicine.service';

type TelemedicineTab = 'dashboard' | 'appointments' | 'waiting-room' | 'consultation' | 'completed' | 'payments' | 'reports' | 'settings';

@Component({
  selector: 'app-telemedicine-workspace',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './telemedicine-workspace.component.html',
  styleUrls: ['./telemedicine-workspace.component.scss'],
})
export class TelemedicineWorkspaceComponent {
  private readonly telemedicine = inject(TelemedicineService);
  private readonly patientService = inject(PatientService);
  private readonly doctorDirectory = inject(DoctorDirectoryService);
  private readonly route = inject(ActivatedRoute);
  private readonly notifications = inject(NotificationService);
  readonly session = inject(SessionService);
  readonly permissions = PERMISSIONS;

  readonly tab = signal<TelemedicineTab>('dashboard');
  readonly tabs: TelemedicineTab[] = ['dashboard', 'appointments', 'waiting-room', 'consultation', 'completed', 'payments', 'reports', 'settings'];
  today = new Date().toISOString().slice(0, 10);
  filters = { doctor_id: '', department: '', date: this.today, status: '', appointment_type: '', payment_status: '' };
  reportFilters = { report_type: 'online_appointments', doctor_id: '', status: '', payment_status: '' };

  dashboard: TelemedicineDashboard | null = null;
  appointments: TelemedicineAppointment[] = [];
  consultations: TelemedicineConsultation[] = [];
  patients: Patient[] = [];
  doctors: User[] = [];
  settings: TelemedicineSetting[] = [];
  report: TelemedicineReport | null = null;
  selectedConsultation: TelemedicineConsultation | null = null;
  chat: TelemedicineChatMessage[] = [];
  files: TelemedicineFile[] = [];
  modal: '' | 'appointment' | 'consent' | 'file' | 'setting' | 'investigation' = '';
  error = '';
  success = '';

  appointmentForm: Record<string, unknown> = {};
  consultationForm: Record<string, unknown> = {};
  chatForm = { message: '' };
  fileForm: Record<string, unknown> = {};
  settingForm: Record<string, unknown> = {};
  investigationForm: Record<string, unknown> = {};

  constructor() {
    this.route.data.subscribe((data) => {
      this.tab.set((data['telemedicineTab'] as TelemedicineTab) || 'dashboard');
      this.loadCurrentTab();
    });
    this.loadReferenceData();
  }

  loadReferenceData(): void {
    this.patientService.list().subscribe((rows) => (this.patients = rows));
    this.doctorDirectory.listDoctors().subscribe((rows) => (this.doctors = rows));
  }

  loadCurrentTab(): void {
    this.error = '';
    this.loadDashboard();
    if (['appointments', 'waiting-room', 'payments'].includes(this.tab())) this.loadAppointments();
    if (['consultation', 'completed'].includes(this.tab())) this.loadConsultations();
    if (this.tab() === 'settings') this.loadSettings();
    if (this.tab() === 'reports') this.loadReport();
  }

  loadDashboard(): void {
    this.telemedicine.dashboard(this.filters).subscribe({ next: (row) => (this.dashboard = row), error: (error) => this.showError(error) });
  }

  loadAppointments(): void {
    const params = this.tab() === 'payments' ? { ...this.filters, payment_status: this.filters.payment_status || 'pending' } : this.filters;
    this.telemedicine.listAppointments(params).subscribe({ next: (rows) => (this.appointments = rows), error: (error) => this.showError(error) });
  }

  loadConsultations(): void {
    const status = this.tab() === 'completed' ? 'completed' : this.filters.status;
    this.telemedicine.listConsultations({ status, doctor_id: this.filters.doctor_id }).subscribe({ next: (rows) => (this.consultations = rows), error: (error) => this.showError(error) });
  }

  loadSettings(): void {
    this.telemedicine.listSettings().subscribe({ next: (rows) => (this.settings = rows), error: (error) => this.showError(error) });
  }

  loadReport(): void {
    this.telemedicine.report(this.reportFilters).subscribe({ next: (report) => (this.report = report), error: (error) => this.showError(error) });
  }

  openModal(name: typeof this.modal): void {
    this.modal = name;
    this.error = '';
    this.success = '';
    if (name === 'appointment') this.appointmentForm = { patient_id: this.patients[0]?.id || '', doctor_user_id: this.doctors[0]?.id || '', department_name: '', appointment_at: this.localDateTime(30), consultation_reason: '', visit_type: 'new', appointment_type: 'video', payment_status: 'pending', consultation_fee: 0, consent_required: true, contact_phone: '', contact_email: '' };
    if (name === 'consent') this.appointmentForm = { ...this.appointmentForm, consent_by: '', consent_terms_version: 'v1' };
    if (name === 'file') this.fileForm = { patient_id: this.selectedConsultation?.patient_id || this.patients[0]?.id || '', consultation_id: this.selectedConsultation?.id || '', file_category: 'medical_document', file_name: '', mime_type: 'application/pdf', file_size_bytes: 0, file_url: '' };
    if (name === 'setting') this.settingForm = { setting_key: '', setting_value: '', description: '' };
    if (name === 'investigation') this.investigationForm = { service_area: 'laboratory', item_name: '', instructions: '' };
  }

  closeModal(): void {
    this.modal = '';
  }

  saveAppointment(): void {
    this.submit(this.telemedicine.createAppointment(this.clean(this.appointmentForm)), 'Online appointment booked');
  }

  updateAppointmentStatus(item: TelemedicineAppointment, status: string): void {
    this.submit(this.telemedicine.updateAppointmentStatus(item.id, { status }), `Appointment marked ${status}`);
  }

  acceptConsent(item: TelemedicineAppointment): void {
    const consentBy = window.prompt('Accepted by patient/guardian');
    if (!consentBy) return;
    this.submit(this.telemedicine.acceptConsent(item.id, { consent_accepted: true, consent_by: consentBy, consent_terms_version: 'v1' }), 'Consent recorded');
  }

  markPaid(item: TelemedicineAppointment): void {
    this.submit(this.telemedicine.updatePayment(item.id, { payment_status: 'paid' }), 'Payment marked paid');
  }

  startConsultation(item: TelemedicineAppointment): void {
    this.telemedicine.startConsultation(item.id).subscribe({
      next: (consultation) => {
        this.selectedConsultation = consultation;
        this.consultationForm = { ...consultation };
        this.tab.set('consultation');
        this.loadConsultations();
        this.loadChatAndFiles();
        this.notifications.success('Consultation started');
      },
      error: (error) => this.showError(error),
    });
  }

  selectConsultation(item: TelemedicineConsultation): void {
    this.selectedConsultation = item;
    this.consultationForm = { ...item };
    this.loadChatAndFiles();
  }

  saveConsultation(): void {
    if (!this.selectedConsultation) return;
    this.submit(this.telemedicine.updateConsultation(this.selectedConsultation.id, this.clean(this.consultationForm)), 'Consultation saved');
  }

  completeConsultation(): void {
    if (!this.selectedConsultation) return;
    this.submit(this.telemedicine.completeConsultation(this.selectedConsultation.id, this.clean(this.consultationForm)), 'Consultation completed');
  }

  sendChat(): void {
    if (!this.selectedConsultation || !this.chatForm.message.trim()) return;
    this.telemedicine.addChat(this.selectedConsultation.id, { message: this.chatForm.message }).subscribe(() => {
      this.chatForm.message = '';
      this.loadChatAndFiles();
    });
  }

  saveFile(): void {
    this.submit(this.telemedicine.addFile(this.clean(this.fileForm)), 'File linked');
  }

  saveInvestigation(): void {
    if (!this.selectedConsultation) return;
    this.submit(this.telemedicine.createInvestigation(this.selectedConsultation.id, this.clean(this.investigationForm)), 'Investigation order created');
  }

  saveSetting(): void {
    this.submit(this.telemedicine.upsertSetting(this.clean(this.settingForm)), 'Setting saved');
  }

  loadChatAndFiles(): void {
    if (!this.selectedConsultation) return;
    this.telemedicine.listChat(this.selectedConsultation.id).subscribe((rows) => (this.chat = rows));
    this.telemedicine.listFiles({ consultation_id: this.selectedConsultation.id }).subscribe((rows) => (this.files = rows));
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
        this.loadCurrentTab();
        this.notifications.success(message);
      },
      error: (error) => this.showError(error),
    });
  }

  private clean(source: Record<string, unknown>): Record<string, unknown> {
    return Object.fromEntries(Object.entries(source).map(([key, value]) => [key, value === '' ? null : value]));
  }

  private showError(error: unknown): void {
    const anyError = error as { error?: { message?: string; detail?: string }; message?: string };
    this.error = anyError.error?.message || anyError.error?.detail || anyError.message || 'Could not complete telemedicine action.';
  }

  private localDateTime(addMinutes = 0): string {
    const now = new Date(Date.now() + addMinutes * 60000);
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    return now.toISOString().slice(0, 16);
  }
}
