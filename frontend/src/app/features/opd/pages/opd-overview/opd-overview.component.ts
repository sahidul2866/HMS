import { CommonModule } from '@angular/common';
import { Component, ElementRef, ViewChild, inject } from '@angular/core';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { User } from '../../../../core/models/auth.models';
import { PERMISSIONS } from '../../../../core/constants/permissions';
import { DoctorDirectoryService } from '../../../../core/services/doctor-directory.service';
import { NotificationService } from '../../../../core/services/notification.service';
import { SessionService } from '../../../../core/services/session.service';
import { buildBarcodeSvg, escapePrintHtml, renderPrintLines } from '../../../../shared/utils/print-layout.utils';
import { AppointmentsService } from '../../../appointments/services/appointments.service';
import { IPDBed } from '../../../ipd/models/ipd.models';
import { IPDService } from '../../../ipd/services/ipd.service';
import { PharmacyInvestigationSetting, PharmacyMedicine } from '../../../pharmacy/models/pharmacy.models';
import { PharmacyService } from '../../../pharmacy/services/pharmacy.service';
import { OPDSummary, OPDVisit, OPDVisitOrder, UpdateOPDConsultationPayload, UpdateOPDPaymentPayload, UpdateOPDVisitPayload } from '../../models/opd.models';
import { OPDService } from '../../services/opd.service';

type DashboardKPI = {
  label: string;
  value: string;
  detail: string;
  tone: string;
};

type DashboardBar = {
  label: string;
  value: number;
  detail: string;
  width: string;
  tone: string;
};

@Component({
  selector: 'app-opd-overview',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule],
  templateUrl: './opd-overview.component.html',
  styleUrls: ['./opd-overview.component.scss'],
})
export class OPDOverviewComponent {
  private readonly fb = inject(FormBuilder);
  private readonly opdService = inject(OPDService);
  private readonly ipdService = inject(IPDService);
  private readonly pharmacyService = inject(PharmacyService);
  private readonly doctorDirectoryService = inject(DoctorDirectoryService);
  private readonly appointmentsService = inject(AppointmentsService);
  private readonly notificationService = inject(NotificationService);
  private readonly sessionService = inject(SessionService);
  private readonly sanitizer = inject(DomSanitizer);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  summary: OPDSummary | null = null;
  visits: OPDVisit[] = [];
  doctors: User[] = [];
  beds: IPDBed[] = [];
  medicines: PharmacyMedicine[] = [];
  investigationSettings: PharmacyInvestigationSetting[] = [];
  selectedVisit: OPDVisit | null = null;
  selectedDoctorUserId = '';
  editingVisit: OPDVisit | null = null;
  payingVisit: OPDVisit | null = null;
  invoicePreviewVisit: OPDVisit | null = null;
  invoicePreviewHtml: string | null = null;
  invoicePreviewUrl: SafeResourceUrl | null = null;
  prescriptionPreviewVisit: OPDVisit | null = null;
  prescriptionPreviewHtml: string | null = null;
  prescriptionPreviewUrl: SafeResourceUrl | null = null;

  private invoicePreviewObjectUrl: string | null = null;
  private prescriptionPreviewObjectUrl: string | null = null;

  @ViewChild('invoiceFrame') invoiceFrame?: ElementRef<HTMLIFrameElement>;
  @ViewChild('prescriptionFrame') prescriptionFrame?: ElementRef<HTMLIFrameElement>;
  @ViewChild('prescriptionWorkspace') prescriptionWorkspace?: ElementRef<HTMLElement>;

  readonly form = this.fb.group({
    patient_id: ['', Validators.required],
    visit_date: [new Date().toISOString().slice(0, 10), Validators.required],
    department_name: ['General OPD', Validators.required],
    doctor_user_id: [''],
    consulting_doctor_name: ['', Validators.required],
    chief_complaint: [''],
    consultation_fee: [0, Validators.required],
    note: [''],
  });

  readonly orderForm = this.fb.group({
    order_type: ['prescription', Validators.required],
    service_area: [''],
    item_name: ['', Validators.required],
    instructions: [''],
    quantity: [1, Validators.required],
  });

  readonly prescriptionForm = this.fb.group({
    item_name: ['', Validators.required],
    instructions: [''],
    quantity: [1, Validators.required],
  });

  readonly investigationForm = this.fb.group({
    item_name: ['', Validators.required],
    service_area: ['laboratory', Validators.required],
    instructions: [''],
    quantity: [1, Validators.required],
  });

  readonly procedureForm = this.fb.group({
    item_name: ['', Validators.required],
    instructions: [''],
    quantity: [1, Validators.required],
  });

  readonly consultationForm = this.fb.group({
    chief_complaint: [''],
    history_of_present_illness: [''],
    past_history: [''],
    vital_signs: [''],
    examination_note: [''],
    provisional_diagnosis: [''],
    final_diagnosis: [''],
    follow_up_date: [''],
    follow_up_note: [''],
    note: [''],
  });

  readonly eyeExamForm = this.fb.group({
    va_re: [''],
    va_le: [''],
    eom_re: [''],
    eom_le: [''],
    lids_re: [''],
    lids_le: [''],
    cornea_re: [''],
    cornea_le: [''],
    conjunctiva_re: [''],
    conjunctiva_le: [''],
    iop_re: [''],
    iop_le: [''],
    pupil_re: [''],
    pupil_le: [''],
    lens_re: [''],
    lens_le: [''],
    fundus_re: [''],
    fundus_le: [''],
    cdr_re: [''],
    cdr_le: [''],
    angle_re: [''],
    angle_le: [''],
    general_exam: [''],
  });

  readonly followUpForm = this.fb.group({
    doctor_user_id: [''],
    appointment_at: [''],
    reason: [''],
    note: [''],
  });

  readonly convertForm = this.fb.group({
    admitted_at: [new Date().toISOString().slice(0, 16), Validators.required],
    admission_type: ['General', Validators.required],
    bed_id: [''],
    ward_name: ['Ward A', Validators.required],
    bed_number: ['', Validators.required],
    doctor_user_id: [''],
    attending_doctor_name: ['', Validators.required],
    diagnosis: [''],
    daily_charge: [0, Validators.required],
    advance_amount: [0, Validators.required],
    expected_discharge_date: [''],
  });

  readonly editVisitForm = this.fb.group({
    visit_date: ['', Validators.required],
    department_name: ['General OPD', Validators.required],
    doctor_user_id: [''],
    consulting_doctor_name: ['', Validators.required],
    chief_complaint: [''],
    consultation_fee: [0, Validators.required],
    note: [''],
  });

  readonly paymentForm = this.fb.group({
    amount: [0, Validators.required],
    discount: [0, Validators.required],
  });

  constructor() {
    this.loadAll();
    this.route.queryParamMap.subscribe((params) => {
      const openVisitId = params.get('openVisit');
      if (openVisitId) {
        this.opdService.getVisit(openVisitId).subscribe((visit) => (this.selectedVisit = visit));
      }
    });
  }

  loadAll(): void {
    this.opdService.getSummary(this.selectedDoctorQuery).subscribe((summary) => (this.summary = summary));
    this.opdService.listVisits(this.selectedDoctorQuery).subscribe((visits) => {
      this.visits = visits;
      if (this.selectedVisit) {
        this.selectedVisit = visits.find((item) => item.id === this.selectedVisit?.id) ?? null;
      }
    });
    this.doctorDirectoryService.listDoctors().subscribe((doctors) => (this.doctors = doctors));
    this.ipdService.listBeds().subscribe((beds) => (this.beds = beds));
    this.pharmacyService.listMedicines({ page: 1, page_size: 100 }).subscribe((response) => (this.medicines = response.items));
    this.pharmacyService.listInvestigationSettings({ page: 1, page_size: 100, is_active: 'true' }).subscribe((response) => (this.investigationSettings = response.items));
  }

  onDoctorQueueChanged(): void {
    this.selectedVisit = null;
    this.loadAll();
  }

  navigateToNewPatient(): void {
    void this.router.navigate(['/patients/new'], { queryParams: { returnTo: '/opd/register' } });
  }

  navigateToRegisterVisit(): void {
    void this.router.navigate(['/opd/register']);
  }

  get canFilterByDoctor(): boolean {
    return this.sessionService.hasPermission(PERMISSIONS.opdViewDoctorWise);
  }

  get canCreateBilling(): boolean {
    return this.sessionService.hasPermission(PERMISSIONS.billingInvoiceCreate);
  }

  get canManageDiagnostics(): boolean {
    return this.sessionService.hasPermission(PERMISSIONS.laboratoryView);
  }

  get canUsePharmacy(): boolean {
    return this.sessionService.hasPermission(PERMISSIONS.pharmacyView);
  }

  get selectedDoctorQuery(): string | null {
    return this.selectedDoctorUserId || null;
  }

  get dashboardKpis(): DashboardKPI[] {
    const totalVisits = this.summary?.total_visits ?? this.visits.length;
    const waitingVisits = this.summary?.waiting_visits ?? this.getVisitCountByStatus('waiting');
    const consultationVisits = this.summary?.in_consultation_visits ?? this.getVisitCountByStatus('in_consultation');
    const completedVisits = this.summary?.completed_visits ?? this.getVisitCountByStatus('completed');

    return [
      {
        label: 'Today Visits',
        value: String(totalVisits),
        detail: `${this.getPaidVisitsCount()} paid registrations`,
        tone: 'teal',
      },
      {
        label: 'Collected',
        value: this.formatCurrency(this.getCollectedAmount()),
        detail: `${this.getPaidVisitsCount()} settled visits`,
        tone: 'emerald',
      },
      {
        label: 'Outstanding',
        value: this.formatCurrency(this.getOutstandingAmount()),
        detail: `${this.getUnpaidVisitsCount()} visits need payment`,
        tone: 'amber',
      },
      {
        label: 'In Queue',
        value: String(waitingVisits + consultationVisits),
        detail: `${waitingVisits} waiting · ${consultationVisits} in consultation`,
        tone: 'blue',
      },
      {
        label: 'Completed',
        value: String(completedVisits),
        detail: `${this.getCompletionRate()} completion rate`,
        tone: 'slate',
      },
      {
        label: 'Avg Visit Value',
        value: this.formatCurrency(this.getAverageVisitValue()),
        detail: `${this.getTotalOrderCount()} total clinical orders`,
        tone: 'rose',
      },
    ];
  }

  get statusChartItems(): DashboardBar[] {
    const items = [
      { label: 'Waiting', value: this.summary?.waiting_visits ?? this.getVisitCountByStatus('waiting'), tone: 'var(--chart-teal)' },
      {
        label: 'In Consultation',
        value: this.summary?.in_consultation_visits ?? this.getVisitCountByStatus('in_consultation'),
        tone: 'var(--chart-blue)',
      },
      { label: 'Completed', value: this.summary?.completed_visits ?? this.getVisitCountByStatus('completed'), tone: 'var(--chart-emerald)' },
      { label: 'Prescribed', value: this.getVisitCountByStatus('prescribed'), tone: 'var(--chart-gold)' },
      { label: 'Billed', value: this.getVisitCountByStatus('billed'), tone: 'var(--chart-violet)' },
    ];
    const max = Math.max(...items.map((item) => item.value), 1);
    return items.map((item) => ({
      ...item,
      detail: `${this.getShareLabel(item.value, this.summary?.total_visits ?? this.visits.length)}`,
      width: `${Math.max((item.value / max) * 100, item.value > 0 ? 12 : 0)}%`,
    }));
  }

  get doctorLoadItems(): DashboardBar[] {
    const counts = new Map<string, number>();
    for (const visit of this.visits) {
      const label = visit.consulting_doctor_name || 'Unassigned';
      counts.set(label, (counts.get(label) ?? 0) + 1);
    }

    const sorted = [...counts.entries()]
      .sort((left, right) => right[1] - left[1] || left[0].localeCompare(right[0]))
      .slice(0, 5);
    const max = Math.max(...sorted.map(([, value]) => value), 1);

    return sorted.map(([label, value]) => ({
      label,
      value,
      detail: `${this.getShareLabel(value, this.visits.length)}`,
      width: `${Math.max((value / max) * 100, value > 0 ? 14 : 0)}%`,
      tone: 'var(--chart-blue)',
    }));
  }

  get orderMixItems(): DashboardBar[] {
    const items = [
      { label: 'Prescription', value: this.getOrderCountByType('prescription'), tone: 'var(--chart-amber)' },
      { label: 'Investigation', value: this.getOrderCountByType('investigation'), tone: 'var(--chart-rose)' },
      { label: 'Procedure', value: this.getOrderCountByType('procedure'), tone: 'var(--chart-violet)' },
    ];
    const max = Math.max(...items.map((item) => item.value), 1);
    const total = items.reduce((sum, item) => sum + item.value, 0);

    return items.map((item) => ({
      ...item,
      detail: total ? this.getShareLabel(item.value, total) : 'No orders yet',
      width: `${Math.max((item.value / max) * 100, item.value > 0 ? 18 : 0)}%`,
    }));
  }

  get revenueHighlights(): Array<{ label: string; value: string }> {
    return [
      { label: 'Gross Fees', value: this.formatCurrency(this.getGrossAmount()) },
      { label: 'Discounts', value: this.formatCurrency(this.getDiscountAmount()) },
      { label: 'Net Collection', value: this.formatCurrency(this.getCollectedAmount()) },
    ];
  }

  get revenueHeadline(): string {
    return this.formatCurrency(this.getCollectedAmount());
  }

  get weeklyTrendItems(): DashboardBar[] {
    const today = new Date();
    const points: Array<{ key: string; label: string }> = [];

    for (let offset = 6; offset >= 0; offset -= 1) {
      const date = new Date(today);
      date.setDate(today.getDate() - offset);
      const key = date.toISOString().slice(0, 10);
      points.push({
        key,
        label: date.toLocaleDateString('en-US', { weekday: 'short' }),
      });
    }

    const counts = new Map<string, number>();
    for (const visit of this.visits) {
      counts.set(visit.visit_date, (counts.get(visit.visit_date) ?? 0) + 1);
    }

    const max = Math.max(...points.map((point) => counts.get(point.key) ?? 0), 1);

    return points.map((point) => {
      const value = counts.get(point.key) ?? 0;
      return {
        label: point.label,
        value,
        detail: point.key,
        width: `${Math.max((value / max) * 100, value > 0 ? 12 : 8)}%`,
        tone: 'var(--chart-teal)',
      };
    });
  }

  isPaymentDone(visit: OPDVisit): boolean {
    return (visit.consultation_payment_status || '').toLowerCase() === 'paid';
  }

  setStatus(visit: OPDVisit, status: string): void {
    this.opdService.updateStatus(visit.id, status).subscribe(() => {
      this.loadAll();
      this.notificationService.success(`Visit ${visit.visit_number} moved to ${status.replace('_', ' ')}.`);
    });
  }

  selectVisit(visit: OPDVisit): void {
    this.selectedVisit = visit;
    const parsedExam = this.parseExaminationNote(visit.examination_note || '');
    this.consultationForm.patchValue({
      chief_complaint: visit.chief_complaint || '',
      history_of_present_illness: visit.history_of_present_illness || '',
      past_history: visit.past_history || '',
      vital_signs: visit.vital_signs || '',
      examination_note: visit.examination_note || '',
      provisional_diagnosis: visit.provisional_diagnosis || '',
      final_diagnosis: visit.final_diagnosis || '',
      follow_up_date: visit.follow_up_date || '',
      follow_up_note: visit.follow_up_note || '',
      note: visit.note || '',
    });
    this.eyeExamForm.patchValue({
      va_re: parsedExam['va_re'] || '',
      va_le: parsedExam['va_le'] || '',
      eom_re: parsedExam['eom_re'] || '',
      eom_le: parsedExam['eom_le'] || '',
      lids_re: parsedExam['lids_re'] || '',
      lids_le: parsedExam['lids_le'] || '',
      cornea_re: parsedExam['cornea_re'] || '',
      cornea_le: parsedExam['cornea_le'] || '',
      conjunctiva_re: parsedExam['conjunctiva_re'] || '',
      conjunctiva_le: parsedExam['conjunctiva_le'] || '',
      iop_re: parsedExam['iop_re'] || '',
      iop_le: parsedExam['iop_le'] || '',
      pupil_re: parsedExam['pupil_re'] || '',
      pupil_le: parsedExam['pupil_le'] || '',
      lens_re: parsedExam['lens_re'] || '',
      lens_le: parsedExam['lens_le'] || '',
      fundus_re: parsedExam['fundus_re'] || '',
      fundus_le: parsedExam['fundus_le'] || '',
      cdr_re: parsedExam['cdr_re'] || '',
      cdr_le: parsedExam['cdr_le'] || '',
      angle_re: parsedExam['angle_re'] || '',
      angle_le: parsedExam['angle_le'] || '',
      general_exam: parsedExam['general_exam'] || '',
    });
    this.followUpForm.patchValue({
      doctor_user_id: visit.consulting_doctor_user_id || '',
      appointment_at: this.buildDefaultFollowUpDateTime(visit.follow_up_date || ''),
      reason: visit.follow_up_note || visit.final_diagnosis || visit.provisional_diagnosis || visit.chief_complaint || '',
      note: visit.note || '',
    });
    this.convertForm.patchValue({
      admitted_at: new Date().toISOString().slice(0, 16),
      admission_type: 'General',
      bed_id: '',
      ward_name: 'Ward A',
      bed_number: '',
      doctor_user_id: visit.consulting_doctor_user_id || visit.doctor_user_id || '',
      attending_doctor_name: visit.consulting_doctor_name,
      diagnosis: visit.final_diagnosis || visit.provisional_diagnosis || visit.chief_complaint || '',
      daily_charge: 0,
      advance_amount: 0,
      expected_discharge_date: '',
    });
  }

  startVisitWorkflow(visit: OPDVisit): void {
    this.selectVisit(visit);
    if (visit.status === 'waiting' || visit.status === 'billed' || visit.status === 'prescribed') {
      this.opdService.updateStatus(visit.id, 'in_consultation').subscribe((updatedVisit) => {
        this.selectedVisit = updatedVisit;
        this.loadAll();
        this.prescriptionWorkspace?.nativeElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
        this.notificationService.success(`Consultation started for ${updatedVisit.visit_number}.`);
      });
      return;
    }
    this.prescriptionWorkspace?.nativeElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  saveConsultation(): void {
    if (!this.selectedVisit) {
      return;
    }
    const payload = this.consultationForm.getRawValue() as UpdateOPDConsultationPayload;
    const examinationNote = this.composeExaminationNote();
    this.opdService
      .updateConsultation(this.selectedVisit.id, {
        ...payload,
        examination_note: examinationNote,
        follow_up_date: payload.follow_up_date || null,
      })
      .subscribe((visit) => {
        this.selectedVisit = visit;
        this.followUpForm.patchValue({
          appointment_at: this.buildDefaultFollowUpDateTime(visit.follow_up_date || ''),
          reason: visit.follow_up_note || visit.final_diagnosis || visit.provisional_diagnosis || visit.chief_complaint || '',
          note: visit.note || '',
        });
        this.loadAll();
        this.notificationService.success(`Consultation notes saved for ${visit.visit_number}.`);
      });
  }

  createFollowUpAppointment(): void {
    if (!this.selectedVisit || this.followUpForm.invalid) {
      return;
    }

    const value = this.followUpForm.getRawValue();
    if (!value.doctor_user_id || !value.appointment_at) {
      return;
    }

    this.appointmentsService
      .create({
        patient_id: this.selectedVisit.patient.id,
        doctor_user_id: value.doctor_user_id,
        appointment_at: value.appointment_at,
        reason: value.reason || this.selectedVisit.follow_up_note || this.selectedVisit.final_diagnosis || null,
        note: value.note || `Follow-up from ${this.selectedVisit.visit_number}`,
      })
      .subscribe((appointment) => {
        this.notificationService.success(`Follow-up appointment ${appointment.appointment_number} created.`);
      });
  }

  submitOrder(): void {
    if (!this.selectedVisit || this.orderForm.invalid) {
      return;
    }
    const payload = this.orderForm.getRawValue();
    this.opdService.createOrder(this.selectedVisit.id, payload as never).subscribe((visit) => {
      this.selectedVisit = visit;
      this.loadAll();
      this.orderForm.reset({ order_type: 'prescription', service_area: '', item_name: '', instructions: '', quantity: 1 });
      this.notificationService.success(`${visit.visit_number} updated with ${payload.order_type || 'order'}.`);
    });
  }

  submitPrescriptionOrder(): void {
    this.submitTypedOrder('prescription', this.prescriptionForm.getRawValue());
  }

  submitInvestigationOrder(): void {
    this.submitTypedOrder('investigation', this.investigationForm.getRawValue());
  }

  submitProcedureOrder(): void {
    this.submitTypedOrder('procedure', this.procedureForm.getRawValue());
  }

  updateProcedureOrder(order: OPDVisitOrder, status: 'scheduled' | 'in_progress' | 'completed' | 'cancelled'): void {
    if (!this.selectedVisit) {
      return;
    }

    const resultText =
      status === 'completed'
        ? window.prompt('Enter procedure outcome or note', order.result_text || order.instructions || '')
        : order.result_text || null;
    if (status === 'completed' && resultText === null) {
      return;
    }

    this.opdService
      .updateOrder(this.selectedVisit.id, order.id, {
        status,
        result_text: resultText || null,
      })
      .subscribe((visit) => {
        this.selectedVisit = visit;
        this.loadAll();
        this.notificationService.success(`Procedure ${order.item_name} moved to ${status.replace('_', ' ')}.`);
      });
  }

  getOrderTypeCount(type: string): number {
    return this.selectedVisit?.orders.filter((order) => order.order_type === type).length ?? 0;
  }

  getOrdersByType(type: 'prescription' | 'investigation' | 'procedure'): OPDVisitOrder[] {
    return this.selectedVisit?.orders.filter((order) => order.order_type === type) ?? [];
  }

  openBilling(visit: OPDVisit): void {
    void this.router.navigate(['/billing/create'], {
      queryParams: {
        patientId: visit.patient.id,
        opdVisitId: visit.id,
      },
    });
  }

  openPharmacySalesDraft(visit: OPDVisit): void {
    void this.router.navigate(['/pharmacy/sales'], {
      queryParams: {
        opdVisitId: visit.id,
      },
    });
  }

  openInvestigationDraft(visit: OPDVisit): void {
    void this.router.navigate(['/diagnostics/orders'], {
      queryParams: {
        opdVisitId: visit.id,
      },
    });
  }

  get medicineSuggestions(): PharmacyMedicine[] {
    const query = (this.prescriptionForm.getRawValue().item_name || '').trim().toLowerCase();
    if (!query) {
      return this.medicines.slice(0, 8);
    }
    return this.medicines
      .filter((item) => `${item.name} ${item.generic_name} ${item.company_name}`.toLowerCase().includes(query))
      .sort((left, right) => Number(right.stock_quantity) - Number(left.stock_quantity))
      .slice(0, 8);
  }

  get investigationSuggestions(): PharmacyInvestigationSetting[] {
    const query = (this.investigationForm.getRawValue().item_name || '').trim().toLowerCase();
    const serviceArea = this.investigationForm.getRawValue().service_area || 'laboratory';
    const pool = this.investigationSettings.filter((item) => item.service_area === serviceArea);
    if (!query) {
      return pool.slice(0, 8);
    }
    return pool.filter((item) => `${item.test_name} ${item.code} ${item.category_name}`.toLowerCase().includes(query)).slice(0, 8);
  }

  openEditVisit(visit: OPDVisit): void {
    this.editingVisit = visit;
    this.editVisitForm.reset({
      visit_date: visit.visit_date,
      department_name: visit.department_name,
      doctor_user_id: visit.consulting_doctor_user_id || '',
      consulting_doctor_name: visit.consulting_doctor_name,
      chief_complaint: visit.chief_complaint || '',
      consultation_fee: Number(visit.consultation_fee ?? 0),
      note: visit.note || '',
    });
  }

  closeEditVisit(): void {
    this.editingVisit = null;
  }

  onEditDoctorChanged(): void {
    const doctorId = this.editVisitForm.getRawValue().doctor_user_id;
    const doctor = this.doctors.find((item) => item.id === doctorId);
    if (!doctor) {
      return;
    }
    this.editVisitForm.patchValue({
      consulting_doctor_name: doctor.full_name,
      consultation_fee: Number(doctor.opd_consultation_fee ?? this.editVisitForm.getRawValue().consultation_fee ?? 0),
    });
  }

  saveVisitEdit(): void {
    if (!this.editingVisit || this.editVisitForm.invalid) {
      return;
    }

    const value = this.editVisitForm.getRawValue();
    const payload: UpdateOPDVisitPayload = {
      visit_date: value.visit_date || this.editingVisit.visit_date,
      department_name: value.department_name || this.editingVisit.department_name,
      doctor_user_id: value.doctor_user_id || null,
      consulting_doctor_name: value.consulting_doctor_name || this.editingVisit.consulting_doctor_name,
      chief_complaint: value.chief_complaint || null,
      consultation_fee: Number(value.consultation_fee ?? 0),
      note: value.note || null,
    };
    this.opdService.updateVisit(this.editingVisit.id, payload).subscribe((visit) => {
      this.editingVisit = null;
      this.selectedVisit = this.selectedVisit?.id === visit.id ? visit : this.selectedVisit;
      this.loadAll();
      this.notificationService.success(`Visit ${visit.visit_number} updated.`);
    });
  }

  openPayment(visit: OPDVisit): void {
    this.payingVisit = visit;
    this.paymentForm.reset({
      amount: Number(visit.consultation_fee ?? 0),
      discount: Number(visit.consultation_discount ?? 0),
    });
  }

  closePayment(): void {
    this.payingVisit = null;
  }

  savePayment(): void {
    if (!this.payingVisit || this.paymentForm.invalid) {
      return;
    }

    const value = this.paymentForm.getRawValue();
    const payload: UpdateOPDPaymentPayload = {
      amount: Number(value.amount ?? 0),
      discount: Number(value.discount ?? 0),
    };
    this.opdService.updatePayment(this.payingVisit.id, payload).subscribe((visit) => {
      this.payingVisit = null;
      this.selectedVisit = this.selectedVisit?.id === visit.id ? visit : this.selectedVisit;
      this.loadAll();
      this.notificationService.success(`Payment recorded for ${visit.visit_number}.`);
      this.printPaymentInvoice(visit);
    });
  }

  getPaymentTotal(): number {
    const value = this.paymentForm.getRawValue();
    const amount = Number(value.amount ?? 0);
    const discount = Number(value.discount ?? 0);
    return Math.max(amount - discount, 0);
  }

  formatCurrency(value: string | number | null | undefined): string {
    return new Intl.NumberFormat('en-BD', {
      style: 'currency',
      currency: 'BDT',
      minimumFractionDigits: 2,
    }).format(Number(value ?? 0));
  }

  private getVisitCountByStatus(status: string): number {
    return this.visits.filter((visit) => visit.status === status).length;
  }

  private getPaidVisitsCount(): number {
    return this.visits.filter((visit) => this.isPaymentDone(visit)).length;
  }

  private getUnpaidVisitsCount(): number {
    return this.visits.length - this.getPaidVisitsCount();
  }

  private getOrderCountByType(type: 'prescription' | 'investigation' | 'procedure'): number {
    return this.visits.reduce((count, visit) => count + visit.orders.filter((order) => order.order_type === type).length, 0);
  }

  private getTotalOrderCount(): number {
    return this.visits.reduce((count, visit) => count + visit.orders.length, 0);
  }

  private getGrossAmount(): number {
    return this.visits.reduce((sum, visit) => sum + Number(visit.consultation_fee ?? 0), 0);
  }

  private getDiscountAmount(): number {
    return this.visits.reduce((sum, visit) => sum + Number(visit.consultation_discount ?? 0), 0);
  }

  private getCollectedAmount(): number {
    return this.visits.reduce((sum, visit) => sum + (this.isPaymentDone(visit) ? Number(visit.consultation_total ?? visit.consultation_fee ?? 0) : 0), 0);
  }

  private getOutstandingAmount(): number {
    return this.visits.reduce(
      (sum, visit) => sum + (this.isPaymentDone(visit) ? 0 : Number(visit.consultation_total ?? visit.consultation_fee ?? 0)),
      0,
    );
  }

  private getAverageVisitValue(): number {
    if (!this.visits.length) {
      return 0;
    }
    return this.getGrossAmount() / this.visits.length;
  }

  private getCompletionRate(): string {
    const total = this.summary?.total_visits ?? this.visits.length;
    if (!total) {
      return '0%';
    }
    const completed = this.summary?.completed_visits ?? this.getVisitCountByStatus('completed');
    return `${Math.round((completed / total) * 100)}%`;
  }

  private getShareLabel(value: number, total: number): string {
    if (!total) {
      return '0% of total';
    }
    return `${Math.round((value / total) * 100)}% of total`;
  }

  printPaymentInvoice(visit: OPDVisit): void {
    this.invoicePreviewVisit = visit;
    this.invoicePreviewHtml = this.buildPaymentInvoiceHtml(visit);
    this.invoicePreviewUrl = this.buildPreviewUrl(this.invoicePreviewHtml, 'invoice');
  }

  closeInvoicePreview(): void {
    this.invoicePreviewVisit = null;
    this.invoicePreviewHtml = null;
    this.invoicePreviewUrl = null;
    this.releasePreviewUrl('invoice');
  }

  printInvoicePreview(): void {
    const frameWindow = this.invoiceFrame?.nativeElement.contentWindow;
    if (!frameWindow) {
      return;
    }
    frameWindow.focus();
    frameWindow.print();
  }

  closePrescriptionPreview(): void {
    this.prescriptionPreviewVisit = null;
    this.prescriptionPreviewHtml = null;
    this.prescriptionPreviewUrl = null;
    this.releasePreviewUrl('prescription');
  }

  printPrescriptionPreview(): void {
    const frameWindow = this.prescriptionFrame?.nativeElement.contentWindow;
    if (!frameWindow) {
      return;
    }
    frameWindow.focus();
    frameWindow.print();
  }

  private buildPaymentInvoiceHtml(visit: OPDVisit): string {
    const amount = Number(visit.consultation_fee ?? 0);
    const discount = Number(visit.consultation_discount ?? 0);
    const total = Number(visit.consultation_total ?? amount - discount);
    const paidAt = visit.consultation_paid_at ? new Date(visit.consultation_paid_at).toLocaleString() : new Date().toLocaleString();
    const invoiceRef = `OPD-PAY-${visit.visit_number}`;
    const printedAt = new Date().toLocaleString();
    const patientName = `${visit.patient.first_name} ${visit.patient.last_name}`.trim();
    const patientAge = this.getPatientAgeLabel(visit.patient.date_of_birth);
    const patientStatus = visit.visit_type === 'follow_up' ? 'Follow-up' : 'New';
    const serviceLabel = visit.visit_type === 'follow_up' ? 'Consultation follow-up visit' : 'Consultation first visit';
    const combinedBarcode = buildBarcodeSvg(`${visit.patient.patient_number} | ${visit.visit_number}`, 'Patient + Visit ID');
    const breakdownRows = discount > 0
      ? `
          <tr>
            <td>1</td>
            <td>${escapePrintHtml(serviceLabel)}</td>
            <td>${this.formatCurrency(amount)}</td>
          </tr>
          <tr>
            <td>2</td>
            <td>Discount</td>
            <td>-${this.formatCurrency(discount)}</td>
          </tr>
        `
      : `
          <tr>
            <td>1</td>
            <td>${escapePrintHtml(serviceLabel)}</td>
            <td>${this.formatCurrency(amount)}</td>
          </tr>
        `;
    const renderCopy = (copyLabel: string) => `
      <section class="invoice-copy">
        <div class="copy-header">
          <div class="brand-block">
            <div class="brand-mark">HMS</div>
            <div>
              <h1>Outpatient Invoice</h1>
              <p class="brand-subtitle">OPD payment acknowledgement</p>
              <p class="brand-meta">Reference: ${escapePrintHtml(invoiceRef)}</p>
            </div>
          </div>
          <div class="copy-tag">${escapePrintHtml(copyLabel)}</div>
        </div>

        <div class="clinic-banner">
          <div>
            <strong>Hospital Management System</strong>
            <span>Outpatient billing desk</span>
          </div>
          <div class="clinic-meta">
            <span>Invoice No: ${escapePrintHtml(visit.visit_number)}</span>
            <span>Paid At: ${escapePrintHtml(paidAt)}</span>
            <span>Print Time: ${escapePrintHtml(printedAt)}</span>
          </div>
        </div>

        <div class="barcode-grid">
          <section class="barcode-card barcode-card--single">${combinedBarcode}</section>
        </div>

        <div class="info-grid">
          <section class="info-card">
            <h3>Patient Information</h3>
            <div class="meta-list">
              <div><span>Patient ID</span><strong>${escapePrintHtml(visit.patient.patient_number)}</strong></div>
              <div><span>Name</span><strong>${escapePrintHtml(patientName)}</strong></div>
              <div><span>Mobile</span><strong>${escapePrintHtml(visit.patient.phone ?? '-')}</strong></div>
              <div><span>Age</span><strong>${escapePrintHtml(patientAge)}</strong></div>
              <div><span>Gender</span><strong>${escapePrintHtml(visit.patient.gender ?? '-')}</strong></div>
              <div><span>Patient Status</span><strong>${escapePrintHtml(patientStatus)}</strong></div>
            </div>
          </section>

          <section class="info-card">
            <h3>Visit Information</h3>
            <div class="meta-list">
              <div><span>Visit Date</span><strong>${escapePrintHtml(visit.visit_date)}</strong></div>
              <div><span>Department</span><strong>${escapePrintHtml(visit.department_name)}</strong></div>
              <div><span>Consultant</span><strong>${escapePrintHtml(visit.consulting_doctor_name)}</strong></div>
              <div><span>Payment Status</span><strong class="caps">${escapePrintHtml(visit.consultation_payment_status || 'paid')}</strong></div>
              <div><span>Chief Complaint</span><strong>${escapePrintHtml(visit.chief_complaint || '-')}</strong></div>
            </div>
          </section>
        </div>

        <section class="table-card">
          <div class="table-title">
            <h3>Charge Details</h3>
            <span>Collected total ${this.formatCurrency(total)}</span>
          </div>
          <table>
            <thead>
              <tr>
                <th>SL</th>
                <th>Service Name</th>
                <th>Amount</th>
              </tr>
            </thead>
            <tbody>
              ${breakdownRows}
              <tr class="total-row">
                <td colspan="2">Total Amount</td>
                <td>${this.formatCurrency(total)}</td>
              </tr>
            </tbody>
          </table>
          <div class="amount-words">In words: ${this.amountInWords(total)} only.</div>
        </section>

        <div class="signature-row">
          <div>
            <span class="signature-label">Prepared by</span>
            <strong>HMS Front Desk</strong>
            <p>Billing / OPD registration desk</p>
          </div>
          <div>
            <span class="signature-label">Authorized signature</span>
            <strong>______________________</strong>
          </div>
        </div>
      </section>
    `;

    return `
      <html>
        <head>
          <title>${visit.visit_number} Payment Invoice</title>
          <style>
            :root {
              --ink: #17304a;
              --muted: #65758a;
              --line: #d7dee7;
              --paper: #ffffff;
              --panel: #f6f8fb;
              --brand: #0d5c63;
              --brand-deep: #123b56;
              --accent: #bb8a2f;
            }
            * { box-sizing: border-box; }
            body {
              margin: 0;
              font-family: "Segoe UI", Arial, sans-serif;
              color: var(--ink);
              background: white;
            }
            .preview-shell {
              max-width: 1000px;
              margin: 0 auto;
              padding: 12px;
              display: grid;
              gap: 20px;
            }
            .invoice-copy {
              padding: 26px 28px 30px;
              border: 1px solid var(--line);
              border-radius: 26px;
              background: var(--paper);
              box-shadow: 0 20px 50px rgba(23, 48, 74, 0.08);
              display: grid;
              gap: 18px;
            }
            .copy-header,
            .clinic-banner,
            .signature-row,
            .table-title {
              display: flex;
              justify-content: space-between;
              gap: 16px;
              flex-wrap: wrap;
              align-items: center;
            }
            .brand-block {
              display: flex;
              gap: 16px;
              align-items: center;
            }
            .brand-mark {
              width: 72px;
              height: 72px;
              border-radius: 20px;
              display: grid;
              place-items: center;
              background: linear-gradient(135deg, var(--brand-deep), var(--brand));
              color: white;
              font-size: 24px;
              font-weight: 800;
              letter-spacing: 0.08em;
            }
            h1, h2, h3, p { margin: 0; }
            .brand-subtitle,
            .brand-meta {
              color: var(--muted);
            }
            .copy-tag {
              padding: 10px 14px;
              border-radius: 999px;
              background: #f4efe2;
              color: #7b5d1e;
              font-size: 12px;
              font-weight: 800;
              text-transform: uppercase;
              letter-spacing: 0.12em;
            }
            .clinic-banner {
              padding: 16px 18px;
              border-radius: 18px;
              background: linear-gradient(180deg, #f7fafc, #eef4f8);
              border: 1px solid var(--line);
            }
            .clinic-banner strong {
              display: block;
              margin-bottom: 4px;
            }
            .clinic-banner span,
            .clinic-meta span {
              color: var(--muted);
              font-size: 13px;
            }
            .clinic-meta {
              display: grid;
              gap: 4px;
              justify-items: end;
            }
            .info-grid {
              display: grid;
              grid-template-columns: repeat(2, minmax(0, 1fr));
              gap: 16px;
            }
            .barcode-grid {
              display: grid;
              grid-template-columns: 1fr;
              gap: 16px;
            }
            .info-card,
            .table-card,
            .barcode-card {
              padding: 18px;
              border-radius: 18px;
              background: var(--panel);
              border: 1px solid var(--line);
            }
            .barcode-card {
              background: linear-gradient(180deg, #fbfcfe, #f2f6fb);
            }
            .barcode-card--single {
              max-width: 460px;
            }
            .id-barcode-svg {
              width: 100%;
              height: 92px;
              display: block;
            }
            .info-card h3,
            .table-card h3 {
              margin-bottom: 14px;
              font-size: 13px;
              letter-spacing: 0.12em;
              text-transform: uppercase;
              color: var(--brand-deep);
            }
            .meta-list {
              display: grid;
              gap: 10px;
            }
            .meta-list div {
              display: flex;
              justify-content: space-between;
              gap: 12px;
              padding-bottom: 9px;
              border-bottom: 1px dashed #ccd7e2;
            }
            .meta-list div:last-child {
              border-bottom: 0;
              padding-bottom: 0;
            }
            .meta-list span {
              color: var(--muted);
            }
            .caps {
              text-transform: capitalize;
            }
            table {
              width: 100%;
              border-collapse: collapse;
              overflow: hidden;
              border-radius: 14px;
              background: white;
            }
            th, td {
              padding: 13px 14px;
              text-align: left;
              border-bottom: 1px solid #e7edf3;
            }
            th {
              font-size: 12px;
              text-transform: uppercase;
              letter-spacing: 0.08em;
              color: var(--muted);
              background: #f8fafc;
            }
            td:last-child, th:last-child {
              text-align: right;
            }
            .total-row td {
              font-weight: 800;
              background: #fbfcfe;
            }
            .amount-words {
              margin-top: 14px;
              padding: 14px 16px;
              border-radius: 14px;
              background: white;
              border: 1px dashed #c7d4e1;
              font-weight: 600;
            }
            .signature-row {
              margin-top: 8px;
              padding-top: 16px;
              border-top: 1px dashed #cfd8e3;
              align-items: end;
            }
            .signature-label {
              display: block;
              margin-bottom: 8px;
              color: var(--muted);
              font-size: 12px;
              text-transform: uppercase;
              letter-spacing: 0.1em;
            }
            .page-break {
              page-break-before: always;
            }
            @media print {
              body {
                background: white;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
              }
              .preview-shell {
                max-width: none;
                padding: 0;
              }
              .invoice-copy {
                box-shadow: none;
                border-radius: 0;
                border: 0;
                padding: 0;
              }
              .page-break {
                page-break-before: always;
              }
              @page {
                margin: 14mm;
              }
            }
          </style>
        </head>
        <body>
          <div class="preview-shell">
            ${renderCopy('Patient Copy')}
            <div class="page-break"></div>
            ${renderCopy('Office Copy')}
          </div>
        </body>
      </html>
    `;
  }

  getPatientAgeLabel(dateOfBirth?: string | null): string {
    if (!dateOfBirth) {
      return '-';
    }
    const birthDate = new Date(dateOfBirth);
    if (Number.isNaN(birthDate.getTime())) {
      return '-';
    }
    const now = new Date();
    let years = now.getFullYear() - birthDate.getFullYear();
    const monthDelta = now.getMonth() - birthDate.getMonth();
    if (monthDelta < 0 || (monthDelta === 0 && now.getDate() < birthDate.getDate())) {
      years -= 1;
    }
    return years >= 0 ? `${years} years` : '-';
  }

  private amountInWords(value: number): string {
    const whole = Math.floor(Math.abs(value));
    if (whole === 0) {
      return 'Zero';
    }

    const ones = [
      '',
      'one',
      'two',
      'three',
      'four',
      'five',
      'six',
      'seven',
      'eight',
      'nine',
      'ten',
      'eleven',
      'twelve',
      'thirteen',
      'fourteen',
      'fifteen',
      'sixteen',
      'seventeen',
      'eighteen',
      'nineteen',
    ];
    const tens = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety'];
    const scales = ['', 'thousand', 'million', 'billion'];

    const chunkToWords = (chunk: number): string => {
      const parts: string[] = [];
      const hundreds = Math.floor(chunk / 100);
      const remainder = chunk % 100;
      if (hundreds) {
        parts.push(`${ones[hundreds]} hundred`);
      }
      if (remainder >= 20) {
        const ten = Math.floor(remainder / 10);
        const unit = remainder % 10;
        parts.push(unit ? `${tens[ten]}-${ones[unit]}` : tens[ten]);
      } else if (remainder > 0) {
        parts.push(ones[remainder]);
      }
      return parts.join(' ');
    };

    const words: string[] = [];
    let remaining = whole;
    let scaleIndex = 0;
    while (remaining > 0 && scaleIndex < scales.length) {
      const chunk = remaining % 1000;
      if (chunk) {
        const chunkWords = chunkToWords(chunk);
        words.unshift(scales[scaleIndex] ? `${chunkWords} ${scales[scaleIndex]}` : chunkWords);
      }
      remaining = Math.floor(remaining / 1000);
      scaleIndex += 1;
    }

    return words.join(' ').replace(/\b\w/g, (character) => character.toUpperCase());
  }

  private getPrescriptionHeader(visit: OPDVisit): {
    name: string;
    degrees: string;
    specialty: string;
    workplace: string;
    chamber: string;
    phone: string;
    address: string;
  } {
    const doctor = this.doctors.find((item) => item.id === visit.consulting_doctor_user_id);
    return {
      name: doctor?.opd_prescription_header_name?.trim() || visit.consulting_doctor_name || 'Consulting Doctor',
      degrees: doctor?.opd_prescription_header_degrees?.trim() || '',
      specialty: doctor?.opd_prescription_header_specialty?.trim() || visit.department_name || '',
      workplace: doctor?.opd_prescription_header_workplace?.trim() || '',
      chamber: doctor?.opd_prescription_header_chamber?.trim() || '',
      phone: doctor?.opd_prescription_header_phone?.trim() || '',
      address: doctor?.opd_prescription_header_address?.trim() || '',
    };
  }

  private submitTypedOrder(
    orderType: 'prescription' | 'investigation' | 'procedure',
    rawValue: { item_name?: string | null; instructions?: string | null; quantity?: number | null; service_area?: string | null },
  ): void {
    if (!this.selectedVisit || !rawValue.item_name?.trim()) {
      return;
    }

    const payload = {
      order_type: orderType,
      item_name: rawValue.item_name.trim(),
      instructions: rawValue.instructions?.trim() || null,
      quantity: Number(rawValue.quantity ?? 1),
      service_area: orderType === 'investigation' ? rawValue.service_area || 'laboratory' : null,
    };

    this.opdService.createOrder(this.selectedVisit.id, payload as never).subscribe((visit) => {
      this.selectedVisit = visit;
      this.loadAll();
      if (orderType === 'prescription') {
        this.prescriptionForm.reset({ item_name: '', instructions: '', quantity: 1 });
      } else if (orderType === 'investigation') {
        this.investigationForm.reset({ item_name: '', service_area: 'laboratory', instructions: '', quantity: 1 });
      } else {
        this.procedureForm.reset({ item_name: '', instructions: '', quantity: 1 });
      }
      this.notificationService.success(`${visit.visit_number} updated with ${orderType}.`);
    });
  }

  private composeExaminationNote(): string {
    const value = this.eyeExamForm.getRawValue();
    const rows = [
      ['VA', value.va_re, value.va_le],
      ['EOM', value.eom_re, value.eom_le],
      ['Lids', value.lids_re, value.lids_le],
      ['Cornea', value.cornea_re, value.cornea_le],
      ['Conjunctiva', value.conjunctiva_re, value.conjunctiva_le],
      ['IOP', value.iop_re, value.iop_le],
      ['Pupil', value.pupil_re, value.pupil_le],
      ['Lens', value.lens_re, value.lens_le],
      ['Fundus', value.fundus_re, value.fundus_le],
      ['CDR', value.cdr_re, value.cdr_le],
      ['Angle', value.angle_re, value.angle_le],
    ];

    const examRows = rows
      .map(([label, re, le]) => `${label}: RE=${re || '-'} | LE=${le || '-'}`)
      .join('\n');

    return `${examRows}\nGeneral: ${value.general_exam || '-'}`;
  }

  private parseExaminationNote(examinationNote: string): {
    va_re?: string;
    va_le?: string;
    eom_re?: string;
    eom_le?: string;
    lids_re?: string;
    lids_le?: string;
    cornea_re?: string;
    cornea_le?: string;
    conjunctiva_re?: string;
    conjunctiva_le?: string;
    iop_re?: string;
    iop_le?: string;
    pupil_re?: string;
    pupil_le?: string;
    lens_re?: string;
    lens_le?: string;
    fundus_re?: string;
    fundus_le?: string;
    cdr_re?: string;
    cdr_le?: string;
    angle_re?: string;
    angle_le?: string;
    general_exam?: string;
  } {
    const parsed: {
      va_re?: string;
      va_le?: string;
      eom_re?: string;
      eom_le?: string;
      lids_re?: string;
      lids_le?: string;
      cornea_re?: string;
      cornea_le?: string;
      conjunctiva_re?: string;
      conjunctiva_le?: string;
      iop_re?: string;
      iop_le?: string;
      pupil_re?: string;
      pupil_le?: string;
      lens_re?: string;
      lens_le?: string;
      fundus_re?: string;
      fundus_le?: string;
      cdr_re?: string;
      cdr_le?: string;
      angle_re?: string;
      angle_le?: string;
      general_exam?: string;
    } = {};
    const mappings: Array<[string, keyof typeof parsed, keyof typeof parsed]> = [
      ['VA', 'va_re', 'va_le'],
      ['EOM', 'eom_re', 'eom_le'],
      ['Lids', 'lids_re', 'lids_le'],
      ['Cornea', 'cornea_re', 'cornea_le'],
      ['Conjunctiva', 'conjunctiva_re', 'conjunctiva_le'],
      ['IOP', 'iop_re', 'iop_le'],
      ['Pupil', 'pupil_re', 'pupil_le'],
      ['Lens', 'lens_re', 'lens_le'],
      ['Fundus', 'fundus_re', 'fundus_le'],
      ['CDR', 'cdr_re', 'cdr_le'],
      ['Angle', 'angle_re', 'angle_le'],
    ];

    for (const [label, rightKey, leftKey] of mappings) {
      const match = examinationNote.match(new RegExp(`${label}:\\s*RE=(.*?)\\s*\\|\\s*LE=(.*?)(?:\\n|$)`));
      if (match) {
        parsed[rightKey] = match[1] === '-' ? '' : match[1].trim();
        parsed[leftKey] = match[2] === '-' ? '' : match[2].trim();
      }
    }

    const generalMatch = examinationNote.match(/General:\s*(.*)$/m);
    parsed.general_exam = generalMatch && generalMatch[1] !== '-' ? generalMatch[1].trim() : '';
    return parsed;
  }

  printPrescription(visit: OPDVisit): void {
    this.prescriptionPreviewVisit = visit;
    this.prescriptionPreviewHtml = this.buildPrescriptionHtml(visit);
    this.prescriptionPreviewUrl = this.buildPreviewUrl(this.prescriptionPreviewHtml, 'prescription');
  }

  private buildPreviewUrl(html: string, kind: 'invoice' | 'prescription'): SafeResourceUrl {
    this.releasePreviewUrl(kind);
    const objectUrl = URL.createObjectURL(new Blob([html], { type: 'text/html' }));
    if (kind === 'invoice') {
      this.invoicePreviewObjectUrl = objectUrl;
    } else {
      this.prescriptionPreviewObjectUrl = objectUrl;
    }
    return this.sanitizer.bypassSecurityTrustResourceUrl(objectUrl);
  }

  private releasePreviewUrl(kind: 'invoice' | 'prescription'): void {
    const currentUrl = kind === 'invoice' ? this.invoicePreviewObjectUrl : this.prescriptionPreviewObjectUrl;
    if (!currentUrl) {
      return;
    }
    URL.revokeObjectURL(currentUrl);
    if (kind === 'invoice') {
      this.invoicePreviewObjectUrl = null;
    } else {
      this.prescriptionPreviewObjectUrl = null;
    }
  }

  private buildPrescriptionHtml(visit: OPDVisit): string {
    const prescriptionOrders = visit.orders.filter((order) => order.order_type === 'prescription');
    const investigationOrders = visit.orders.filter((order) => order.order_type === 'investigation');
    const procedureOrders = visit.orders.filter((order) => order.order_type === 'procedure');
    const exam = this.parseExaminationNote(visit.examination_note || '');
    const doctorHeader = this.getPrescriptionHeader(visit);
    const patientAge = this.getPatientAgeLabel(visit.patient.date_of_birth);
    const patientName = `${visit.patient.first_name} ${visit.patient.last_name}`.trim();
    const combinedBarcode = buildBarcodeSvg(`${visit.patient.patient_number} | ${visit.visit_number}`, 'Patient + Visit ID');
    const prescriptionRows = prescriptionOrders.length
      ? prescriptionOrders.map((order, index) => `<tr><td>${index + 1}</td><td>${escapePrintHtml(order.item_name)}</td><td>${escapePrintHtml(order.instructions || '') || '&nbsp;'}</td><td>${order.quantity}</td></tr>`).join('')
      : `<tr><td>1</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td></tr><tr><td>2</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td></tr><tr><td>3</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td></tr>`;
    const investigationRows = investigationOrders.length
      ? investigationOrders.map((order, index) => `<tr><td>${index + 1}</td><td>${escapePrintHtml(order.item_name)}</td><td>${escapePrintHtml(order.service_area || '-')}</td><td>${escapePrintHtml(order.instructions || '') || '&nbsp;'}</td></tr>`).join('')
      : `<tr><td>1</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td></tr>`;
    const procedureRows = procedureOrders.length
      ? procedureOrders.map((order, index) => `<tr><td>${index + 1}</td><td>${escapePrintHtml(order.item_name)}</td><td>${escapePrintHtml(order.instructions || '') || '&nbsp;'}</td></tr>`).join('')
      : `<tr><td>1</td><td>&nbsp;</td><td>&nbsp;</td></tr>`;

    return `
      <!DOCTYPE html>
      <html lang="en">
        <head>
          <meta charset="utf-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1" />
          <title>${escapePrintHtml(visit.visit_number)} Prescription</title>
          <style>
            :root { --ink:#14263d; --muted:#5d6f82; --line:#d7dee7; --soft:#f6f8fb; }
            * { box-sizing:border-box; }
            html, body { width:100%; }
            body { font-family: Georgia, "Times New Roman", serif; margin:0; padding:18px; color:var(--ink); background:#eef2f7; }
            h1,h2,h3,p { margin:0; }
            .sheet { max-width:1120px; margin:0 auto; display:grid; gap:14px; padding:18px; border:1px solid var(--line); background:#fff; box-shadow:0 18px 42px rgba(15, 23, 42, 0.08); }
            .header { display:grid; gap:12px; padding-bottom:12px; border-bottom:1px solid var(--line); }
            .header-top,.patient-grid,.footer { display:flex; justify-content:space-between; gap:18px; flex-wrap:wrap; }
            .doctor-block { flex:1 1 320px; display:grid; gap:2px; }
            .doctor-block.right { text-align:right; }
            .doctor-name { font-size:27px; font-weight:700; }
            .doctor-line { color:var(--muted); font-size:14px; line-height:1.25; }
            .barcode-strip { display:grid; grid-template-columns:1fr; gap:12px; }
            .barcode-box { max-width:460px; padding:8px 10px; border:1px solid var(--line); background:#fbfcfe; }
            .id-barcode-svg { width:100%; height:86px; display:block; }
            .patient-strip { padding:9px 12px; border:1px solid var(--line); background:var(--soft); }
            .patient-grid > div { flex:1 1 160px; font-size:14px; }
            .workspace { display:grid; grid-template-columns:minmax(300px,0.92fr) minmax(470px,1.28fr); gap:14px; min-height:740px; }
            .column { display:grid; gap:12px; }
            .column.left { border-right:1px solid var(--line); padding-right:12px; }
            .panel { padding:10px 12px; border:1px solid var(--line); background:white; break-inside: avoid; }
            .panel h3 { margin-bottom:10px; font-size:14px; font-weight:700; }
            .text-block { min-height:84px; white-space:pre-wrap; line-height:1.4; overflow-wrap:anywhere; }
            .exam-table,.line-table { width:100%; border-collapse:collapse; table-layout: fixed; }
            .exam-table th,.exam-table td,.line-table th,.line-table td { padding:6px 8px; text-align:left; vertical-align:top; border-bottom:1px solid #edf1f5; overflow-wrap:anywhere; }
            .exam-table th,.line-table th { font-size:12px; text-transform:uppercase; letter-spacing:.08em; color:var(--muted); background:#fafbfd; }
            .rx-title { margin-bottom:6px; color:#8a5a12; font-size:42px; line-height:1; }
            .footer { align-items:flex-end; padding-top:8px; border-top:1px solid var(--line); color:var(--muted); font-size:12px; }
            @media (max-width: 980px) {
              body { padding:10px; }
              .sheet { padding:12px; }
              .workspace { grid-template-columns:1fr; }
              .column.left { border-right:0; padding-right:0; border-bottom:1px solid var(--line); padding-bottom:12px; }
              .doctor-block.right { text-align:left; }
            }
            @media print {
              body { background:white; padding:0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
              .sheet { max-width:none; padding:0; border:0; box-shadow:none; }
              .workspace { display:table; width:100%; min-height:auto; table-layout:fixed; }
              .column { display:table-cell; width:50%; vertical-align:top; }
              .column.left { border-right:1px solid var(--line); padding-right:12px; border-bottom:0; padding-bottom:0; }
              .column + .column { padding-left:12px; }
              .panel, .barcode-box, .patient-strip { break-inside: avoid; page-break-inside: avoid; }
              .exam-table thead, .line-table thead { display: table-header-group; }
              @page { size:A4 portrait; margin:10mm; }
            }
          </style>
        </head>
        <body>
          <div class="sheet">
            <section class="header">
              <div class="header-top">
                <div class="doctor-block">
                  <div class="doctor-name">${escapePrintHtml(doctorHeader.name)}</div>
                  ${renderPrintLines(doctorHeader.degrees, '&nbsp;', 'doctor-line')}
                  ${renderPrintLines(doctorHeader.specialty, '&nbsp;', 'doctor-line')}
                  ${renderPrintLines(doctorHeader.workplace, '&nbsp;', 'doctor-line')}
                  ${renderPrintLines(doctorHeader.chamber, '&nbsp;', 'doctor-line')}
                  ${doctorHeader.phone ? `<div class="doctor-line">Contact: ${escapePrintHtml(doctorHeader.phone)}</div>` : '<div class="doctor-line">&nbsp;</div>'}
                  ${doctorHeader.address ? `<div class="doctor-line">${escapePrintHtml(doctorHeader.address)}</div>` : '<div class="doctor-line">&nbsp;</div>'}
                </div>
                <div class="doctor-block right">
                  <div class="doctor-name">${escapePrintHtml(doctorHeader.name)}</div>
                  ${renderPrintLines(doctorHeader.degrees, '&nbsp;', 'doctor-line')}
                  ${renderPrintLines(doctorHeader.specialty, '&nbsp;', 'doctor-line')}
                  ${renderPrintLines(doctorHeader.workplace, '&nbsp;', 'doctor-line')}
                  ${renderPrintLines(doctorHeader.chamber, '&nbsp;', 'doctor-line')}
                  ${doctorHeader.phone ? `<div class="doctor-line">Contact: ${escapePrintHtml(doctorHeader.phone)}</div>` : '<div class="doctor-line">&nbsp;</div>'}
                  ${doctorHeader.address ? `<div class="doctor-line">${escapePrintHtml(doctorHeader.address)}</div>` : '<div class="doctor-line">&nbsp;</div>'}
                </div>
              </div>
              <div class="barcode-strip">
                <div class="barcode-box">${combinedBarcode}</div>
              </div>
              <div class="patient-strip patient-grid">
                <div><strong>Name:</strong> ${escapePrintHtml(patientName)}</div>
                <div><strong>Age:</strong> ${escapePrintHtml(patientAge)}</div>
                <div><strong>Patient ID:</strong> ${escapePrintHtml(visit.patient.patient_number)}</div>
                <div><strong>Bill No:</strong> ${escapePrintHtml(visit.visit_number)}</div>
                <div><strong>Date:</strong> ${escapePrintHtml(visit.visit_date)}</div>
              </div>
            </section>
            <section class="workspace">
              <div class="column left">
                <section class="panel"><h3>Chief Complaint</h3><div class="text-block">${escapePrintHtml(visit.chief_complaint || '') || '&nbsp;'}</div></section>
                <section class="panel"><h3>Past History</h3><div class="text-block">${escapePrintHtml(visit.past_history || '') || '&nbsp;'}</div></section>
                <section class="panel"><h3>Treatment History</h3><div class="text-block">${escapePrintHtml(visit.history_of_present_illness || '') || '&nbsp;'}</div></section>
                <section class="panel">
                  <h3>On Examination</h3>
                  <table class="exam-table">
                    <thead><tr><th></th><th>R/E</th><th>L/E</th></tr></thead>
                    <tbody>
                      <tr><td>VA</td><td>${escapePrintHtml(exam.va_re || '') || '&nbsp;'}</td><td>${escapePrintHtml(exam.va_le || '') || '&nbsp;'}</td></tr>
                      <tr><td>EOM</td><td>${escapePrintHtml(exam.eom_re || '') || '&nbsp;'}</td><td>${escapePrintHtml(exam.eom_le || '') || '&nbsp;'}</td></tr>
                      <tr><td>Lids</td><td>${escapePrintHtml(exam.lids_re || '') || '&nbsp;'}</td><td>${escapePrintHtml(exam.lids_le || '') || '&nbsp;'}</td></tr>
                      <tr><td>Cornea</td><td>${escapePrintHtml(exam.cornea_re || '') || '&nbsp;'}</td><td>${escapePrintHtml(exam.cornea_le || '') || '&nbsp;'}</td></tr>
                      <tr><td>Conjunctiva</td><td>${escapePrintHtml(exam.conjunctiva_re || '') || '&nbsp;'}</td><td>${escapePrintHtml(exam.conjunctiva_le || '') || '&nbsp;'}</td></tr>
                      <tr><td>IOP</td><td>${escapePrintHtml(exam.iop_re || '') || '&nbsp;'}</td><td>${escapePrintHtml(exam.iop_le || '') || '&nbsp;'}</td></tr>
                      <tr><td>Pupil</td><td>${escapePrintHtml(exam.pupil_re || '') || '&nbsp;'}</td><td>${escapePrintHtml(exam.pupil_le || '') || '&nbsp;'}</td></tr>
                      <tr><td>Lens</td><td>${escapePrintHtml(exam.lens_re || '') || '&nbsp;'}</td><td>${escapePrintHtml(exam.lens_le || '') || '&nbsp;'}</td></tr>
                      <tr><td>Fundus</td><td>${escapePrintHtml(exam.fundus_re || '') || '&nbsp;'}</td><td>${escapePrintHtml(exam.fundus_le || '') || '&nbsp;'}</td></tr>
                      <tr><td>C D R</td><td>${escapePrintHtml(exam.cdr_re || '') || '&nbsp;'}</td><td>${escapePrintHtml(exam.cdr_le || '') || '&nbsp;'}</td></tr>
                      <tr><td>Angle</td><td>${escapePrintHtml(exam.angle_re || '') || '&nbsp;'}</td><td>${escapePrintHtml(exam.angle_le || '') || '&nbsp;'}</td></tr>
                    </tbody>
                  </table>
                  <div class="text-block" style="min-height:48px; margin-top:8px;"><strong>General:</strong> ${escapePrintHtml(exam.general_exam || '') || '&nbsp;'}</div>
                </section>
              </div>
              <div class="column">
                <section class="panel"><h3>Diagnosis</h3><div class="text-block"><strong>Provisional:</strong> ${escapePrintHtml(visit.provisional_diagnosis || '') || '&nbsp;'}</div><div class="text-block" style="min-height:60px;"><strong>Final:</strong> ${escapePrintHtml(visit.final_diagnosis || '') || '&nbsp;'}</div></section>
                <section class="panel"><h3>Investigations</h3><table class="line-table"><thead><tr><th>SL</th><th>Investigation</th><th>Area</th><th>Note</th></tr></thead><tbody>${investigationRows}</tbody></table></section>
                <section class="panel"><div class="rx-title">R<sub>X</sub></div><table class="line-table"><thead><tr><th>SL</th><th>Medicine</th><th>Direction</th><th>Qty</th></tr></thead><tbody>${prescriptionRows}</tbody></table></section>
                <section class="panel"><h3>Procedure</h3><table class="line-table"><thead><tr><th>SL</th><th>Procedure</th><th>Note</th></tr></thead><tbody>${procedureRows}</tbody></table></section>
                <section class="panel"><h3>Advice</h3><div class="text-block">${escapePrintHtml(visit.follow_up_note || visit.note || '') || '&nbsp;'}</div></section>
                <section class="panel"><h3>Follow Up</h3><div class="text-block" style="min-height:44px;">${escapePrintHtml(visit.follow_up_date || '') || '&nbsp;'}</div></section>
              </div>
            </section>
            <div class="footer">
              <div>Generated from HMS OPD Desk</div>
              <div>Printed on ${escapePrintHtml(new Date().toLocaleString())}</div>
            </div>
          </div>
        </body>
      </html>
    `;
  }

  onOrderTypeChanged(): void {
    if (this.orderForm.getRawValue().order_type !== 'investigation') {
      this.orderForm.patchValue({ service_area: '' });
    }
  }

  get availableBeds(): IPDBed[] {
    return this.beds.filter((bed) => bed.status === 'available');
  }

  onConvertBedChanged(): void {
    const bedId = this.convertForm.getRawValue().bed_id;
    const bed = this.beds.find((item) => item.id === bedId);
    if (!bed) {
      return;
    }
    this.convertForm.patchValue({
      ward_name: bed.ward_name,
      bed_number: bed.bed_number,
      daily_charge: Number(bed.daily_rate),
    });
  }

  onConvertDoctorChanged(): void {
    const doctorId = this.convertForm.getRawValue().doctor_user_id;
    const doctor = this.doctors.find((item) => item.id === doctorId);
    if (!doctor) {
      return;
    }
    this.convertForm.patchValue({ attending_doctor_name: doctor.full_name });
  }

  convertToIPD(): void {
    if (!this.selectedVisit || this.selectedVisit.converted_ipd_admission_id || this.convertForm.invalid) {
      return;
    }

    const value = this.convertForm.getRawValue();
    this.opdService
      .convertToIPD(this.selectedVisit.id, {
        ...value,
        expected_discharge_date: value.expected_discharge_date || null,
      } as never)
      .subscribe((admission) => {
        this.loadAll();
        this.notificationService.success(`Visit ${this.selectedVisit?.visit_number} converted to ${admission.admission_number}.`);
      });
  }

  private buildDefaultFollowUpDateTime(followUpDate: string): string {
    if (!followUpDate) {
      return '';
    }
    return `${followUpDate}T10:00`;
  }
}
