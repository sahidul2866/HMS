import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormArray, FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { User } from '../../../../core/models/auth.models';
import { DoctorDirectoryService } from '../../../../core/services/doctor-directory.service';
import { NotificationService } from '../../../../core/services/notification.service';
import { UiStateService } from '../../../../core/services/ui-state.service';
import { IPDAdmission } from '../../../ipd/models/ipd.models';
import { IPDService } from '../../../ipd/services/ipd.service';
import { OPDVisit } from '../../../opd/models/opd.models';
import { OPDService } from '../../../opd/services/opd.service';
import { Patient, PatientLookupResult } from '../../../patients/models/patient.models';
import { PatientService } from '../../../patients/services/patient.service';
import {
  BillingInvoiceItemPayload,
  BillingInvoicePreview,
  BillingService,
  CreateBillingInvoicePayload,
} from '../../models/billing.models';
import { BillingServiceApi } from '../../services/billing.service';

@Component({
  selector: 'app-billing-create',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './billing-create.component.html',
  styleUrls: ['./billing-create.component.scss'],
})
export class BillingCreateComponent {
  private static readonly STATE_KEY = 'ui-state:billing:create';
  private readonly fb = inject(FormBuilder);
  private readonly patientService = inject(PatientService);
  private readonly billingService = inject(BillingServiceApi);
  private readonly opdService = inject(OPDService);
  private readonly ipdService = inject(IPDService);
  private readonly doctorDirectoryService = inject(DoctorDirectoryService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly notificationService = inject(NotificationService);
  private readonly uiStateService = inject(UiStateService);

  patients: Patient[] = [];
  patientSearchResults: PatientLookupResult[] = [];
  billingServices: BillingService[] = [];
  internalReferralDoctors: User[] = [];
  preview: BillingInvoicePreview | null = null;
  saving = false;
  previewMessage = '';
  prefillMessage = '';
  selectedPatient: Patient | null = null;
  sourceVisit: OPDVisit | null = null;
  sourceAdmission: IPDAdmission | null = null;

  readonly patientLookupControl = this.fb.nonNullable.control('');

  readonly form = this.fb.group({
    patient_id: ['', Validators.required],
    internal_referral_user_id: [''],
    discount_percentage: [0, [Validators.min(0), Validators.max(100)]],
    note: [''],
    items: this.fb.array([]),
  });

  constructor() {
    this.restoreState();
    if (!this.items.length) {
      this.addItem();
    }
    this.loadPatients();
    this.loadServices();
    this.loadDoctors();
    this.route.queryParamMap.subscribe((params) => {
      const patientId = params.get('patientId');
      const opdVisitId = params.get('opdVisitId');
      const ipdAdmissionId = params.get('ipdAdmissionId');
      if (patientId) {
        this.form.patchValue({ patient_id: patientId });
        this.syncSelectedPatient();
        this.persistState();
      }
      if (opdVisitId) {
        this.loadVisitPrefill(opdVisitId);
      }
      if (ipdAdmissionId) {
        this.loadAdmissionPrefill(ipdAdmissionId);
      }
    });
    this.form.valueChanges.subscribe(() => this.persistState());
    this.form.controls.patient_id.valueChanges.subscribe(() => this.syncSelectedPatient());
  }

  get items(): FormArray {
    return this.form.controls.items as FormArray;
  }

  addItem(): void {
    this.items.push(
      this.fb.group({
        billing_service_id: ['', Validators.required],
        quantity: [1, [Validators.required, Validators.min(0.01)]],
      })
    );
    this.persistState();
  }

  removeItem(index: number): void {
    if (this.items.length === 1) {
      return;
    }
    this.items.removeAt(index);
    this.persistState();
    this.recalculatePreview();
  }

  loadPatients(): void {
    this.patientService.list().subscribe((patients) => {
      this.patients = patients;
      this.syncSelectedPatient();
    });
  }

  loadServices(): void {
    this.billingService.listServices().subscribe((services) => {
      this.billingServices = services;
      if (this.sourceVisit) {
        this.applyVisitServiceSuggestion(this.sourceVisit);
      }
      this.recalculatePreview();
    });
  }

  loadDoctors(): void {
    this.doctorDirectoryService.listDoctors(true).subscribe((doctors) => {
      this.internalReferralDoctors = doctors;
      if (this.sourceVisit?.consulting_doctor_user_id) {
        const referralDoctor = doctors.find((item) => item.id === this.sourceVisit?.consulting_doctor_user_id);
        if (referralDoctor) {
          this.form.patchValue({ internal_referral_user_id: referralDoctor.id });
        }
      }
    });
  }

  searchPatients(): void {
    const query = this.patientLookupControl.getRawValue().trim();
    if (query.length < 2) {
      this.patientSearchResults = [];
      return;
    }
    this.patientService.search(query).subscribe((results) => (this.patientSearchResults = results));
  }

  applyPatient(result: PatientLookupResult): void {
    this.form.patchValue({ patient_id: result.id });
    this.selectedPatient =
      this.patients.find((item) => item.id === result.id) ??
      ({
        ...result,
      } as Patient);
    this.patientLookupControl.setValue(`${result.patient_number} - ${result.full_name}`);
    this.patientSearchResults = [];
    this.persistState();
  }

  clearPatientSelection(): void {
    this.form.patchValue({ patient_id: '' });
    this.selectedPatient = null;
    this.patientLookupControl.setValue('');
    this.patientSearchResults = [];
    this.persistState();
  }

  onBillingItemChanged(): void {
    this.recalculatePreview();
  }

  onPatientChanged(): void {
    this.syncSelectedPatient();
    this.persistState();
  }

  onInternalReferralChanged(): void {
    const userId = this.form.getRawValue().internal_referral_user_id;
    if (!this.internalReferralDoctors.find((item) => item.id === userId)) {
      this.form.patchValue({ internal_referral_user_id: '' });
    }
  }

  recalculatePreview(): void {
    const items = this.getInvoiceItemsPayload();
    if (!items.length) {
      this.preview = null;
      return;
    }

    const discount = Number(this.form.getRawValue().discount_percentage ?? 0);
    this.billingService.previewInvoice(discount, items).subscribe({
      next: (preview) => {
        this.preview = preview;
        this.previewMessage = '';
      },
      error: () => {
        this.preview = null;
        this.previewMessage = 'Preview unavailable until all selected services are valid.';
      },
    });
  }

  navigateToNewPatient(): void {
    void this.router.navigate(['/patients/new'], { queryParams: { returnTo: '/billing/create' } });
  }

  openBillingDesk(): void {
    void this.router.navigate(['/billing']);
  }

  submit(): void {
    if (this.form.invalid || this.saving) {
      return;
    }

    const payload: CreateBillingInvoicePayload = {
      patient_id: this.form.getRawValue().patient_id ?? '',
      internal_referral_user_id: this.form.getRawValue().internal_referral_user_id || null,
      discount_percentage: Number(this.form.getRawValue().discount_percentage ?? 0),
      note: this.form.getRawValue().note || null,
      items: this.getInvoiceItemsPayload(),
    };
    if (!payload.items.length) {
      return;
    }

    this.saving = true;
    this.billingService.createInvoice(payload).subscribe({
      next: (invoice) => {
        const finalizeNavigation = () => {
          this.saving = false;
          this.clearDraftKeepContext();
          this.notificationService.success(`Invoice ${invoice.invoice_number} created successfully.`);
          void this.router.navigate(['/billing'], { queryParams: { invoiceId: invoice.id } });
        };

        if (this.sourceVisit) {
          this.opdService.updateStatus(this.sourceVisit.id, 'billed').subscribe({
            next: () => {
              this.prefillMessage = `${this.sourceVisit?.visit_number} billed and synced back to OPD.`;
              finalizeNavigation();
            },
            error: () => {
              this.saving = false;
              this.notificationService.warning(`Invoice ${invoice.invoice_number} posted, but OPD status was not updated.`);
            },
          });
          return;
        }

        finalizeNavigation();
      },
      error: () => {
        this.saving = false;
      },
    });
  }

  formatPatient(patient: Patient): string {
    return `${patient.patient_number} - ${patient.first_name} ${patient.last_name}`;
  }

  getServiceName(serviceId: string): string {
    return this.billingServices.find((service) => service.id === serviceId)?.name ?? 'Select service';
  }

  getServiceAmount(serviceId: string, quantity: number): string {
    const service = this.billingServices.find((item) => item.id === serviceId);
    if (!service) {
      return this.formatCurrency(0);
    }
    return this.formatCurrency(Number(service.unit_price) * quantity);
  }

  formatCurrency(value: string | number): string {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(Number(value));
  }

  private getInvoiceItemsPayload(): BillingInvoiceItemPayload[] {
    const rawItems = this.items.getRawValue() as { billing_service_id?: string; quantity?: number }[];
    return rawItems
      .filter((item) => item.billing_service_id && Number(item.quantity) > 0)
      .map((item) => ({
        billing_service_id: item.billing_service_id!,
        quantity: Number(item.quantity),
      }));
  }

  private restoreState(): void {
    const state = this.uiStateService.load<{
      patient_id?: string;
      internal_referral_user_id?: string;
      discount_percentage?: number;
      note?: string;
      items?: BillingInvoiceItemPayload[];
    }>(BillingCreateComponent.STATE_KEY);

    if (!state) {
      return;
    }

    this.form.patchValue({
      patient_id: state.patient_id ?? '',
      internal_referral_user_id: state.internal_referral_user_id ?? '',
      discount_percentage: state.discount_percentage ?? 0,
      note: state.note ?? '',
    });

    this.items.clear();
    for (const item of state.items ?? []) {
      this.items.push(
        this.fb.group({
          billing_service_id: [item.billing_service_id, Validators.required],
          quantity: [item.quantity, [Validators.required, Validators.min(0.01)]],
        })
      );
    }
  }

  private persistState(): void {
    this.uiStateService.save(BillingCreateComponent.STATE_KEY, {
      patient_id: this.form.getRawValue().patient_id ?? '',
      internal_referral_user_id: this.form.getRawValue().internal_referral_user_id ?? '',
      discount_percentage: Number(this.form.getRawValue().discount_percentage ?? 0),
      note: this.form.getRawValue().note ?? '',
      items: this.getInvoiceItemsPayload(),
    });
  }

  private clearDraftKeepContext(): void {
    const patientId = this.form.getRawValue().patient_id ?? '';
    this.form.reset({
      patient_id: patientId,
      internal_referral_user_id: '',
      discount_percentage: 0,
      note: '',
    });
    this.items.clear();
    this.addItem();
    this.preview = null;
    this.uiStateService.clear(BillingCreateComponent.STATE_KEY);
    this.syncSelectedPatient();
  }

  private syncSelectedPatient(): void {
    const patientId = this.form.getRawValue().patient_id;
    this.selectedPatient = this.patients.find((item) => item.id === patientId) ?? null;
  }

  private loadVisitPrefill(visitId: string): void {
    this.opdService.getVisit(visitId).subscribe((visit) => {
      this.sourceVisit = visit;
      this.sourceAdmission = null;
      this.form.patchValue({
        patient_id: visit.patient.id,
        note: this.buildVisitNote(visit),
      });
      this.selectedPatient = this.patients.find((item) => item.id === visit.patient.id) ?? visit.patient;
      this.patientLookupControl.setValue(`${visit.patient.patient_number} - ${visit.patient.first_name} ${visit.patient.last_name}`);

      const referralDoctor = visit.consulting_doctor_user_id
        ? this.internalReferralDoctors.find((item) => item.id === visit.consulting_doctor_user_id)
        : null;
      if (referralDoctor) {
        this.form.patchValue({ internal_referral_user_id: referralDoctor.id });
      }

      this.applyVisitServiceSuggestion(visit);
      this.recalculatePreview();
      this.persistState();
    });
  }

  private loadAdmissionPrefill(admissionId: string): void {
    this.ipdService.getAdmission(admissionId).subscribe((admission) => {
      this.sourceAdmission = admission;
      this.sourceVisit = null;
      this.form.patchValue({
        patient_id: admission.patient.id,
        note: this.buildAdmissionNote(admission),
      });
      this.selectedPatient = this.patients.find((item) => item.id === admission.patient.id) ?? admission.patient;
      this.patientLookupControl.setValue(`${admission.patient.patient_number} - ${admission.patient.first_name} ${admission.patient.last_name}`);

      const referralDoctor = admission.attending_doctor_user_id
        ? this.internalReferralDoctors.find((item) => item.id === admission.attending_doctor_user_id)
        : null;
      if (referralDoctor) {
        this.form.patchValue({ internal_referral_user_id: referralDoctor.id });
      }

      this.prefillMessage = `Loaded ${admission.admission_number} for discharge billing handoff.`;
      this.recalculatePreview();
      this.persistState();
    });
  }

  private buildVisitNote(visit: OPDVisit): string {
    const noteParts = [
      `From OPD visit ${visit.visit_number}`,
      `Doctor: ${visit.consulting_doctor_name}`,
      visit.chief_complaint ? `Complaint: ${visit.chief_complaint}` : '',
      visit.orders.length ? `Orders: ${visit.orders.map((order) => order.item_name).join(', ')}` : '',
    ].filter(Boolean);
    return noteParts.join(' · ');
  }

  private buildAdmissionNote(admission: IPDAdmission): string {
    const noteParts = [
      `From IPD admission ${admission.admission_number}`,
      `Ward/Bed: ${admission.ward_name} / ${admission.bed_number}`,
      `Doctor: ${admission.attending_doctor_name}`,
      admission.diagnosis ? `Admission diagnosis: ${admission.diagnosis}` : '',
      admission.discharge_diagnosis ? `Discharge diagnosis: ${admission.discharge_diagnosis}` : '',
      admission.discharge_condition ? `Condition: ${admission.discharge_condition}` : '',
    ].filter(Boolean);
    return noteParts.join(' · ');
  }

  private findConsultationService(visit: OPDVisit): BillingService | null {
    const consultationFee = Number(visit.consultation_fee ?? 0);
    const rankedMatches = this.billingServices
      .filter((service) => service.is_active)
      .map((service) => {
        const haystack = `${service.service_code} ${service.name}`.toLowerCase();
        let score = 0;
        if (haystack.includes('consult')) {
          score += 4;
        }
        if (haystack.includes('opd') || haystack.includes('outpatient')) {
          score += 3;
        }
        if (Number(service.unit_price) === consultationFee) {
          score += 5;
        }
        return { service, score };
      })
      .filter((item) => item.score > 0)
      .sort((left, right) => right.score - left.score);

    return rankedMatches[0]?.service ?? null;
  }

  private applyVisitServiceSuggestion(visit: OPDVisit): void {
    const matchedService = this.findConsultationService(visit);
    if (matchedService) {
      this.items.clear();
      this.items.push(
        this.fb.group({
          billing_service_id: [matchedService.id, Validators.required],
          quantity: [1, [Validators.required, Validators.min(0.01)]],
        })
      );
      this.prefillMessage = `Loaded ${visit.visit_number} and matched consultation billing service ${matchedService.service_code}.`;
      return;
    }

    this.prefillMessage = `Loaded ${visit.visit_number}. No consultation billing service matched ${this.formatCurrency(visit.consultation_fee)} automatically.`;
  }
}
