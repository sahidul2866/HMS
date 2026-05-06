import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';

import { Patient, PatientLookupResult } from '../../../patients/models/patient.models';
import { PatientService } from '../../../patients/services/patient.service';
import { OTBooking, OTCaseSheet, OTDashboard, OTRoom, OTSchedule } from '../../models/ot.models';
import { OTService } from '../../services/ot.service';

type OTTab = 'dashboard' | 'bookings' | 'calendar' | 'rooms' | 'checklist' | 'anesthesia' | 'notes' | 'recovery' | 'consumables' | 'billing' | 'documents' | 'reports';

@Component({
  selector: 'app-ot-management',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './ot-management.component.html',
  styleUrls: ['./ot-management.component.scss'],
})
export class OTManagementComponent {
  private readonly otService = inject(OTService);
  private readonly patientService = inject(PatientService);
  private readonly route = inject(ActivatedRoute);

  tab = signal<OTTab>('dashboard');

  loading = false;
  saving = false;
  error = '';
  success = '';
  q = '';
  calendarDay = this.today();
  statusFilter = '';
  dashboard: OTDashboard | null = null;
  rooms: OTRoom[] = [];
  bookings: OTBooking[] = [];
  schedules: OTSchedule[] = [];
  patients: Patient[] = [];
  patientMatches: PatientLookupResult[] = [];
  selectedSchedule: OTSchedule | null = null;
  caseSheet: OTCaseSheet | null = null;
  modal: '' | 'room' | 'booking' | 'schedule' | 'preop' | 'anesthesia' | 'note' | 'recovery' | 'consumable' | 'equipment' | 'billing' | 'document' = '';

  roomForm: Record<string, unknown> = {};
  bookingForm: Record<string, unknown> = {};
  scheduleForm: Record<string, unknown> = {};
  preOpForm: Record<string, unknown> = {};
  anesthesiaForm: Record<string, unknown> = {};
  noteForm: Record<string, unknown> = {};
  recoveryForm: Record<string, unknown> = {};
  consumableForm: Record<string, unknown> = {};
  equipmentForm: Record<string, unknown> = {};
  billingForm: Record<string, unknown> = {};
  documentForm: Record<string, unknown> = {};

  constructor() {
    this.route.data.subscribe((data) => {
      this.tab.set((data['otTab'] as OTTab) || 'dashboard');
      this.load();
    });
  }

  load(): void {
    this.error = '';
    this.otService.listRooms().subscribe((rooms) => (this.rooms = rooms));
    this.otService.listBookings(this.q).subscribe((bookings) => (this.bookings = bookings));
    this.patientService.list().subscribe((patients) => (this.patients = patients));
    this.loadSchedules();
    if (this.tab() === 'dashboard') {
      this.otService.dashboard().subscribe({ next: (summary) => (this.dashboard = summary), error: (error) => this.showError(error) });
    }
  }

  loadSchedules(): void {
    this.otService.listSchedules(this.tab() === 'calendar' ? this.calendarDay : undefined, this.statusFilter || undefined).subscribe({
      next: (schedules) => {
        this.schedules = schedules;
        if (!this.selectedSchedule && schedules.length) this.selectSchedule(schedules[0]);
      },
      error: (error) => this.showError(error),
    });
  }

  selectSchedule(schedule: OTSchedule): void {
    this.selectedSchedule = schedule;
    this.otService.getCaseSheet(schedule.id).subscribe({ next: (sheet) => (this.caseSheet = sheet), error: () => (this.caseSheet = null) });
  }

  patientSearchChanged(value: string): void {
    this.patientService.search(value, 8).subscribe((rows) => (this.patientMatches = rows));
  }

  selectPatient(patient: PatientLookupResult): void {
    this.bookingForm['patient_id'] = patient.id;
    this.bookingForm['patient_label'] = `${patient.patient_number} - ${patient.full_name}`;
    this.patientMatches = [];
  }

  openModal(modal: typeof this.modal, schedule?: OTSchedule): void {
    this.modal = modal;
    if (schedule) this.selectSchedule(schedule);
    const selected = schedule || this.selectedSchedule;
    if (modal === 'room') this.roomForm = { room_number: '', name: '', room_type: 'major', status: 'available', floor: 'Level 3', hourly_charge: 4000, equipment_summary: '' };
    if (modal === 'booking') this.bookingForm = { patient_id: '', patient_label: '', procedure_name: '', surgery_type: 'elective', priority_level: 'normal', preferred_start_at: this.localDateTime(2), estimated_duration_minutes: 90, department_name: 'Surgery', diagnosis: '' };
    if (modal === 'schedule') this.scheduleForm = { booking_id: this.bookings[0]?.id || '', room_id: this.rooms[0]?.id || '', scheduled_start_at: this.localDateTime(2), scheduled_end_at: this.localDateTime(4), status: 'scheduled' };
    if (modal === 'preop') this.preOpForm = { consent_signed: true, anesthesia_cleared: true, lab_verified: true, radiology_verified: true, blood_arranged: false, npo_confirmed: true, site_marked: true, equipment_confirmed: true, implant_confirmed: true, allergy_info: 'No known allergy', pre_op_diagnosis: selected?.procedure_name || '', risk_assessment_notes: '', ready_for_ot: true };
    if (modal === 'anesthesia') this.anesthesiaForm = { anesthesia_type: 'general', pre_assessment: 'ASA II, airway assessed', notes: '', medication_record: '', fluid_record: '', vitals_summary: 'Stable baseline vitals', complications: '', recovery_notes: '', clearance_status: 'cleared' };
    if (modal === 'note') this.noteForm = { procedure_performed: selected?.procedure_name || '', operative_findings: '', surgeon_notes: '', nursing_notes: '', instrument_count_confirmed: true, sponge_count_confirmed: true, implant_usage_details: '', specimen_collection_details: '', surgery_outcome: 'successful' };
    if (modal === 'recovery') this.recoveryForm = { transfer_to: 'ward', recovery_admission_at: this.localDateTime(4), vitals_summary: 'Stable', pain_score: 2, consciousness_status: 'Awake', post_op_instructions: '', medication_instructions: '', nursing_observations: '', handover_notes: '' };
    if (modal === 'consumable') this.consumableForm = { schedule_id: selected?.id || '', item_name: 'Surgical drape set', batch_no: '', quantity_used: 1, unit_cost: 650, charged_amount: 900 };
    if (modal === 'equipment') this.equipmentForm = { schedule_id: selected?.id || '', equipment_name: 'C-arm', usage_notes: '', charge_amount: 1500, confirmed: true };
    if (modal === 'billing') this.billingForm = { schedule_id: selected?.id || '', charge_type: 'procedure', description: selected?.procedure_name || 'Surgery charge', amount: 25000, payment_status: 'pending' };
    if (modal === 'document') this.documentForm = { schedule_id: selected?.id || '', document_type: 'consent', title: 'Surgical consent', body: 'Digital consent template', status: 'stored' };
  }

  closeModal(): void {
    this.modal = '';
  }

  saveRoom(): void { this.submit(this.otService.createRoom(this.roomForm), 'OT room saved'); }
  saveBooking(): void { this.submit(this.otService.createBooking(this.clean(this.bookingForm)), 'OT booking created'); }
  saveSchedule(): void { this.submit(this.otService.createSchedule(this.scheduleForm), 'Surgery scheduled'); }
  savePreOp(): void { if (this.selectedSchedule) this.submit(this.otService.upsertPreOp(this.selectedSchedule.id, this.preOpForm), 'Pre-op checklist updated'); }
  saveAnesthesia(): void { if (this.selectedSchedule) this.submit(this.otService.upsertAnesthesia(this.selectedSchedule.id, this.anesthesiaForm), 'Anesthesia record updated'); }
  saveNote(): void { if (this.selectedSchedule) this.submit(this.otService.upsertSurgeryNote(this.selectedSchedule.id, this.noteForm), 'Operative note updated'); }
  saveRecovery(): void { if (this.selectedSchedule) this.submit(this.otService.upsertRecovery(this.selectedSchedule.id, this.recoveryForm), 'Recovery handover updated'); }
  saveConsumable(): void { this.submit(this.otService.addConsumable(this.consumableForm), 'Consumable usage saved'); }
  saveEquipment(): void { this.submit(this.otService.addEquipment(this.equipmentForm), 'Equipment usage saved'); }
  saveBilling(): void { this.submit(this.otService.addBillingItem(this.billingForm), 'OT billing item saved'); }
  saveDocument(): void { this.submit(this.otService.addDocument(this.documentForm), 'OT document saved'); }

  updateStatus(schedule: OTSchedule, status: string): void {
    this.submit(this.otService.updateStatus(schedule.id, status), `Surgery marked ${status}`);
  }

  printCaseSheet(): void {
    window.print();
  }

  formatMoney(value: number | string | null | undefined): string {
    return new Intl.NumberFormat('en-BD', { style: 'currency', currency: 'BDT', maximumFractionDigits: 0 }).format(Number(value || 0));
  }

  statusClass(status: string | undefined | null): string {
    return `status status-${(status || 'neutral').replaceAll('_', '-')}`;
  }

  maxRecord(record: Record<string, number> | undefined): number {
    return Math.max(...Object.values(record || {}), 1);
  }

  private submit<T>(request$: import('rxjs').Observable<T>, message: string): void {
    this.saving = true;
    request$.subscribe({
      next: () => {
        this.saving = false;
        this.success = message;
        this.closeModal();
        this.load();
      },
      error: (error) => {
        this.saving = false;
        this.showError(error);
      },
    });
  }

  private clean(payload: Record<string, unknown>): Record<string, unknown> {
    const copy = { ...payload };
    delete copy['patient_label'];
    return copy;
  }

  private showError(error: unknown): void {
    const item = error as { error?: { message?: string; detail?: string }; message?: string };
    this.error = item.error?.message || item.error?.detail || item.message || 'OT action failed.';
  }

  private today(): string {
    return new Date().toISOString().slice(0, 10);
  }

  private localDateTime(hoursAhead: number): string {
    const date = new Date(Date.now() + hoursAhead * 60 * 60 * 1000);
    return date.toISOString().slice(0, 16);
  }
}
