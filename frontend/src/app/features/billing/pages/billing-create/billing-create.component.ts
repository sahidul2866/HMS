import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormArray, FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { debounceTime, distinctUntilChanged } from 'rxjs';

import { User } from '../../../../core/models/auth.models';
import { PERMISSIONS } from '../../../../core/constants/permissions';
import { DoctorDirectoryService } from '../../../../core/services/doctor-directory.service';
import { NotificationService } from '../../../../core/services/notification.service';
import { SessionService } from '../../../../core/services/session.service';
import { UiStateService } from '../../../../core/services/ui-state.service';
import { FormValidationUi } from '../../../../shared/utils/form-validation';
import { printInvestigationStickers } from '../../../../shared/utils/investigation-sticker-printer';
import { IPDAdmission } from '../../../ipd/models/ipd.models';
import { IPDService } from '../../../ipd/services/ipd.service';
import { OPDVisit } from '../../../opd/models/opd.models';
import { OPDService } from '../../../opd/services/opd.service';
import { CreatePatientPayload, Patient, PatientLookupResult } from '../../../patients/models/patient.models';
import { PatientService } from '../../../patients/services/patient.service';
import { PharmacyInvestigationSetting, PharmacyMedicine } from '../../../pharmacy/models/pharmacy.models';
import { PharmacyService } from '../../../pharmacy/services/pharmacy.service';
import {
  BillingDraft,
  BillingInvoice,
  BillingInvoiceItemPayload,
  BillingInvoicePreview,
  BillingSettings,
  BillingService,
  CreateBillingInvoicePayload,
} from '../../models/billing.models';
import { BillingServiceApi } from '../../services/billing.service';

type PatientSearchContext = 'lookup' | 'phone' | 'email' | null;
type BillingCatalogType = 'billing_service' | 'medicine' | 'investigation_setting';

interface BillingCatalogOption {
  key: string;
  type: BillingCatalogType;
  id: string;
  name: string;
  code: string;
  group: string;
  module: string;
  unitPrice: string;
  doctorSharePercentage: string;
  maxDiscountPercentage?: string | null;
  maxDiscountAmount?: string | null;
  roomNumber?: string | null;
  meta: string;
}

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
  private readonly pharmacyService = inject(PharmacyService);
  private readonly opdService = inject(OPDService);
  private readonly ipdService = inject(IPDService);
  private readonly doctorDirectoryService = inject(DoctorDirectoryService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly notificationService = inject(NotificationService);
  private readonly sessionService = inject(SessionService);
  private readonly uiStateService = inject(UiStateService);
  readonly validation = FormValidationUi;

  patients: Patient[] = [];
  patientSearchResults: PatientLookupResult[] = [];
  billingServices: BillingService[] = [];
  medicines: PharmacyMedicine[] = [];
  investigationSettings: PharmacyInvestigationSetting[] = [];
  internalReferralDoctors: User[] = [];
  billingSettings: BillingSettings | null = null;
  preview: BillingInvoicePreview | null = null;
  draft: BillingDraft | null = null;
  previewMessage = '';
  prefillMessage = '';
  selectedPatient: Patient | null = null;
  sourceVisit: OPDVisit | null = null;
  sourceAdmission: IPDAdmission | null = null;
  activePatientSearchContext: PatientSearchContext = null;
  activeItemSearchIndex: number | null = null;
  saving = false;
  submitted = false;

  readonly patientLookupControl = this.fb.nonNullable.control('');

  readonly form = this.fb.group({
    patient_id: [''],
    first_name: ['', Validators.required],
    last_name: ['', Validators.required],
    phone: [''],
    email: ['', Validators.email],
    gender: [''],
    date_of_birth: [''],
    address: [''],
    internal_referral_user_id: [''],
    discount_percentage: [0, [Validators.min(0), Validators.max(100)]],
    payment_amount: [0, [Validators.min(0)]],
    payment_method: ['cash'],
    payment_note: [''],
    note: [''],
    items: this.fb.array([]),
  });

  constructor() {
    this.restoreState();
    if (!this.items.length) {
      this.addItem();
    }
    this.clearDisallowedItems();
    this.loadPatients();
    this.loadServices();
    this.loadExternalCatalog();
    this.loadSettings();
    this.loadDoctors();
    this.bindPatientSearch();
    this.route.queryParamMap.subscribe((params) => {
      const patientId = params.get('patientId');
      const opdVisitId = params.get('opdVisitId');
      const ipdAdmissionId = params.get('ipdAdmissionId');
      const billingStage = (params.get('billingStage') as 'interim' | 'final' | null) ?? 'interim';
      if (patientId) {
        this.form.patchValue({ patient_id: patientId });
        this.syncSelectedPatient();
        this.persistState();
      }
      if (opdVisitId) {
        this.loadVisitPrefill(opdVisitId);
      }
      if (ipdAdmissionId) {
        this.loadAdmissionPrefill(ipdAdmissionId, billingStage);
      }
    });
    this.form.valueChanges.subscribe(() => this.persistState());
    this.form.controls.patient_id.valueChanges.subscribe(() => this.syncSelectedPatient());
  }

  get items(): FormArray {
    return this.form.controls.items as FormArray;
  }

  get hasExistingPatientSelection(): boolean {
    return !!this.form.getRawValue().patient_id;
  }

  get selectedPatientName(): string {
    if (this.selectedPatient) {
      return `${this.selectedPatient.first_name} ${this.selectedPatient.last_name}`.trim();
    }
    const value = this.form.getRawValue();
    return `${value.first_name ?? ''} ${value.last_name ?? ''}`.trim() || 'Pending';
  }

  get sourceContextLabel(): string {
    if (this.sourceVisit) {
      return `OPD ${this.sourceVisit.visit_number}`;
    }
    if (this.sourceAdmission) {
      return `IPD ${this.sourceAdmission.admission_number}`;
    }
    return 'Direct bill';
  }

  get selectedItemCount(): number {
    return this.getInvoiceItemsPayload().length;
  }

  get readyToPost(): boolean {
    return !!this.selectedPatientName && this.selectedPatientName !== 'Pending' && this.selectedItemCount > 0 && !this.getDiscountLimitViolation() && !this.getPaymentLimitViolation();
  }

  get postReadinessMessage(): string {
    const hasPatient = this.hasExistingPatientSelection || !!(this.form.getRawValue().first_name && this.form.getRawValue().last_name);
    if (!hasPatient) {
      return 'Select or enter patient details.';
    }
    if (!this.selectedItemCount) {
      return 'Add at least one billable item.';
    }
    return this.getDiscountLimitViolation() || this.getPaymentLimitViolation() || 'Ready to post.';
  }

  get paymentDuePreview(): number {
    return Number(this.preview?.total_amount ?? 0);
  }

  get stickerItemCount(): number {
    return this.getInvoiceItemsPayload().filter((item) => this.isInvestigationModule(item.source_module)).length;
  }

  get invoiceOverviewItems(): Array<{ label: string; value: string; tone: string }> {
    const due = this.preview ? Math.max(0, Number(this.preview.total_amount || 0) - Number(this.form.getRawValue().payment_amount || 0)) : 0;
    return [
      { label: 'Patient', value: this.selectedPatientName, tone: this.selectedPatientName === 'Pending' ? 'warn' : 'good' },
      { label: 'Source', value: this.sourceContextLabel, tone: this.sourceVisit || this.sourceAdmission ? 'info' : 'neutral' },
      { label: 'Items', value: String(this.selectedItemCount), tone: this.selectedItemCount ? 'good' : 'warn' },
      { label: 'Due After Pay', value: this.formatCurrency(due), tone: due > 0 ? 'warn' : 'good' },
    ];
  }

  itemCategoryLabel(index: number): string {
    const option = this.getSelectedCatalogOption(index);
    if (!option) {
      return 'Empty';
    }
    return option.group;
  }

  itemCategoryClass(index: number): string {
    const option = this.getSelectedCatalogOption(index);
    if (!option) {
      return 'invoice-row--empty';
    }
    if (option.type === 'medicine') {
      return 'invoice-row--medicine';
    }
    if (option.module === 'radiology') {
      return 'invoice-row--radiology';
    }
    if (option.module === 'laboratory') {
      return 'invoice-row--laboratory';
    }
    return 'invoice-row--service';
  }

  get billingSteps(): Array<{ label: string; state: 'done' | 'active' | 'pending' }> {
    const hasPatient = this.hasExistingPatientSelection || !!(this.form.getRawValue().first_name && this.form.getRawValue().last_name);
    const hasItems = this.selectedItemCount > 0;
    return [
      { label: 'Patient', state: hasPatient ? 'done' : 'active' },
      { label: 'Items', state: hasItems ? 'done' : hasPatient ? 'active' : 'pending' },
      { label: 'Post', state: this.readyToPost ? 'active' : 'pending' },
    ];
  }

  get quickCatalogOptions(): BillingCatalogOption[] {
    const selectedKeys = new Set(
      this.items.getRawValue().map((item: { source_item_type?: string; source_item_id?: string; billing_service_id?: string }) => {
        const type = item.source_item_type || 'billing_service';
        const id = item.source_item_id || item.billing_service_id || '';
        return `${type}:${id}`;
      })
    );
    return this.billingCatalogOptions
      .filter((option) => !selectedKeys.has(option.key))
      .slice(0, 6);
  }

  addQuickCatalogOption(option: BillingCatalogOption): void {
    const emptyIndex = this.items.controls.findIndex((item) => !item.get('source_item_id')?.value && !item.get('billing_service_id')?.value);
    const targetIndex = emptyIndex >= 0 ? emptyIndex : this.items.length;
    if (emptyIndex < 0) {
      this.addItem();
    }
    this.selectCatalogOption(targetIndex, option);
  }

  clearBillingContext(): void {
    this.sourceVisit = null;
    this.sourceAdmission = null;
    this.draft = null;
    this.prefillMessage = '';
    this.form.patchValue({ note: '' });
    this.items.clear();
    this.addItem();
    this.recalculatePreview();
  }

  addItem(): void {
    this.items.push(
      this.fb.group({
        billing_service_id: [''],
        catalog_search: [''],
        source_item_type: ['billing_service'],
        source_item_id: [''],
        quantity: [1, [Validators.required, Validators.min(0.01)]],
        discount_percentage: [0, [Validators.min(0), Validators.max(100)]],
        source_opd_visit_order_id: [''],
        source_label: [''],
        source_module: [''],
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

  loadExternalCatalog(): void {
    if (this.canBillMedicines) {
      this.pharmacyService.listMedicines({ page: 1, page_size: 500, is_active: true }).subscribe({
        next: (response) => {
          this.medicines = response.items;
          this.recalculatePreview();
        },
        error: () => {
          this.medicines = [];
        },
      });
    } else {
      this.medicines = [];
    }
    if (this.canBillInvestigations) {
      this.pharmacyService.listInvestigationSettings({ page: 1, page_size: 500, is_active: 'true' }).subscribe({
        next: (response) => {
          this.investigationSettings = response.items;
          this.recalculatePreview();
        },
        error: () => {
          this.investigationSettings = [];
        },
      });
    } else {
      this.investigationSettings = [];
    }
  }

  get canBillServices(): boolean {
    return this.sessionService.hasPermission(PERMISSIONS.billingItemService);
  }

  get canBillMedicines(): boolean {
    return this.sessionService.hasPermission(PERMISSIONS.billingItemMedicine);
  }

  get canBillInvestigations(): boolean {
    return this.sessionService.hasPermission(PERMISSIONS.billingItemInvestigation);
  }

  get allowedBillingItemLabels(): string {
    const labels = [
      this.canBillServices ? 'services' : null,
      this.canBillMedicines ? 'medicines' : null,
      this.canBillInvestigations ? 'lab/radiology' : null,
    ].filter(Boolean);
    return labels.length ? labels.join(', ') : 'no billing item types';
  }

  get hasAnyBillingItemPermission(): boolean {
    return this.canBillServices || this.canBillMedicines || this.canBillInvestigations;
  }

  get billingItemPlaceholder(): string {
    return `Search ${this.allowedBillingItemLabels}`;
  }

  private canUseCatalogOption(option: BillingCatalogOption): boolean {
    if (option.type === 'medicine') {
      return this.canBillMedicines;
    }
    if (option.type === 'investigation_setting') {
      return this.canBillInvestigations;
    }
    return this.canBillServices;
  }

  private canUsePayloadItem(item: BillingInvoiceItemPayload): boolean {
    const sourceType = item.source_item_type;
    const sourceModule = String(item.source_module || '').toLowerCase();
    if (sourceType === 'medicine' || sourceModule === 'pharmacy') {
      return this.canBillMedicines;
    }
    if (sourceType === 'investigation_setting' || ['laboratory', 'radiology', 'opd_investigation'].includes(sourceModule)) {
      return this.canBillInvestigations;
    }
    return this.canBillServices;
  }

  private clearDisallowedItems(): void {
    for (const item of this.items.controls) {
      const sourceType = item.get('source_item_type')?.value as BillingCatalogType | null;
      const sourceModule = String(item.get('source_module')?.value || '').toLowerCase();
      const isMedicine = sourceType === 'medicine' || sourceModule === 'pharmacy';
      const isInvestigation = sourceType === 'investigation_setting' || ['laboratory', 'radiology', 'opd_investigation'].includes(sourceModule);
      const allowed = isMedicine ? this.canBillMedicines : isInvestigation ? this.canBillInvestigations : this.canBillServices;
      if (!allowed) {
        item.patchValue({
          billing_service_id: '',
          catalog_search: '',
          source_item_type: 'billing_service',
          source_item_id: '',
          source_opd_visit_order_id: '',
          source_label: '',
          source_module: '',
        });
      }
    }
    this.recalculatePreview();
    this.persistState();
  }

  loadSettings(): void {
    this.billingService.getSettings().subscribe({
      next: (settings) => {
        this.billingSettings = settings;
      },
      error: () => {
        this.billingSettings = {
          max_item_discount_percentage: '100',
          max_item_discount_amount: null,
          max_invoice_discount_percentage: '100',
          max_invoice_discount_amount: null,
          default_referral_percentage: '0',
        };
      },
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

  searchPatients(query: string, context: PatientSearchContext): void {
    const normalized = query.trim();
    if (normalized.length < 3) {
      if (this.activePatientSearchContext === context) {
        this.closePatientSearch();
      }
      return;
    }

    this.patientService.searchByAnyField(normalized, 6).subscribe((results) => {
      this.patientSearchResults = results;
      this.activePatientSearchContext = results.length ? context : null;
    });
  }

  applyPatient(result: PatientLookupResult): void {
    this.selectedPatient = { ...result };
    this.form.patchValue(
      {
        patient_id: result.id,
        first_name: result.first_name,
        last_name: result.last_name,
        phone: result.phone || '',
        email: result.email || '',
        gender: result.gender || '',
        date_of_birth: result.date_of_birth || '',
        address: result.address || '',
      },
      { emitEvent: false }
    );
    this.patientLookupControl.setValue(`${result.patient_number} - ${result.full_name}`, { emitEvent: false });
    this.closePatientSearch();
    this.persistState();
  }

  clearPatientSelection(): void {
    this.selectedPatient = null;
    this.patientLookupControl.setValue('', { emitEvent: false });
    this.form.patchValue(
      {
        patient_id: '',
        first_name: '',
        last_name: '',
        phone: '',
        email: '',
        gender: '',
        date_of_birth: '',
        address: '',
      },
      { emitEvent: false }
    );
    this.closePatientSearch();
    this.persistState();
  }

  closePatientSearch(): void {
    this.patientSearchResults = [];
    this.activePatientSearchContext = null;
  }

  showSearchContext(context: PatientSearchContext): boolean {
    return this.activePatientSearchContext === context && this.patientSearchResults.length > 0;
  }

  onBillingItemChanged(): void {
    this.recalculatePreview();
  }

  get billingCatalogOptions(): BillingCatalogOption[] {
    const serviceOptions = this.canBillServices ? this.billingServices.map((service) => ({
      key: `billing_service:${service.id}`,
      type: 'billing_service' as const,
      id: service.id,
      name: service.name,
      code: service.service_code,
      group: 'Billing Service',
      module: 'billing',
      unitPrice: service.unit_price,
      doctorSharePercentage: service.doctor_share_percentage,
      maxDiscountPercentage: service.max_discount_percentage ?? null,
      maxDiscountAmount: service.max_discount_amount ?? null,
      roomNumber: service.room_number ?? null,
      meta: [service.description || 'Service catalog', service.room_number ? `Room ${service.room_number}` : null].filter(Boolean).join(' · '),
    })) : [];
    const medicineOptions = this.canBillMedicines ? this.medicines.map((medicine) => ({
      key: `medicine:${medicine.id}`,
      type: 'medicine' as const,
      id: medicine.id,
      name: medicine.name,
      code: medicine.sku || medicine.barcode || 'MED',
      group: 'Medicine',
      module: 'pharmacy',
      unitPrice: medicine.sale_price,
      doctorSharePercentage: this.billingSettings?.default_referral_percentage ?? '0',
      maxDiscountPercentage: this.billingSettings?.max_item_discount_percentage ?? '100',
      maxDiscountAmount: this.billingSettings?.max_item_discount_amount ?? null,
      roomNumber: null,
      meta: [medicine.generic_name, medicine.company_name, `Stock ${medicine.stock_quantity}`].filter(Boolean).join(' · '),
    })) : [];
    const investigationOptions = this.canBillInvestigations ? this.investigationSettings.map((setting) => ({
      key: `investigation_setting:${setting.id}`,
      type: 'investigation_setting' as const,
      id: setting.id,
      name: setting.test_name,
      code: setting.code,
      group: setting.service_area === 'radiology' ? 'Radiology' : 'Laboratory',
      module: setting.service_area,
      unitPrice: setting.fee,
      doctorSharePercentage: this.billingSettings?.default_referral_percentage ?? '0',
      maxDiscountPercentage: this.billingSettings?.max_item_discount_percentage ?? '100',
      maxDiscountAmount: this.billingSettings?.max_item_discount_amount ?? null,
      roomNumber: setting.room_number ?? null,
      meta: [setting.category_name, setting.room_number ? `Room ${setting.room_number}` : null].filter(Boolean).join(' · '),
    })) : [];
    return [...serviceOptions, ...medicineOptions, ...investigationOptions];
  }

  filteredCatalogOptions(index: number): BillingCatalogOption[] {
    const query = String(this.items.at(index).get('catalog_search')?.value ?? '').trim().toLowerCase();
    const options = this.billingCatalogOptions.filter((option) => this.canUseCatalogOption(option));
    if (!query) {
      return options.slice(0, 20);
    }
    return options
      .filter((option) => `${option.name} ${option.code} ${option.group} ${option.meta}`.toLowerCase().includes(query))
      .slice(0, 20);
  }

  showItemSearch(index: number): boolean {
    return this.activeItemSearchIndex === index && this.filteredCatalogOptions(index).length > 0;
  }

  selectCatalogOption(index: number, option: BillingCatalogOption): void {
    const item = this.items.at(index);
    if (!item) {
      return;
    }
    if (!this.canUseCatalogOption(option)) {
      this.notificationService.warning(`You do not have permission to bill ${option.group.toLowerCase()} items.`);
      return;
    }
    item.patchValue({
      catalog_search: `${option.group} - ${option.name}`,
      billing_service_id: option.type === 'billing_service' ? option.id : '',
      source_item_type: option.type,
      source_item_id: option.id,
      source_module: option.module,
      source_label: `${option.group} · ${option.name}`,
    });
    this.activeItemSearchIndex = null;
    this.recalculatePreview();
    this.persistState();
  }

  selectCatalogOptionAndAddNext(index: number, option: BillingCatalogOption): void {
    this.selectCatalogOption(index, option);
    this.addItem();
    this.activeItemSearchIndex = this.items.length - 1;
  }

  onCatalogTab(index: number, event: KeyboardEvent): void {
    const options = this.filteredCatalogOptions(index);
    if (!options.length) {
      return;
    }
    event.preventDefault();
    this.selectCatalogOptionAndAddNext(index, options[0]);
  }

  get maxItemDiscountPercentage(): number {
    return Number(this.billingSettings?.max_item_discount_percentage ?? 100);
  }

  get maxInvoiceDiscountPercentage(): number {
    return Number(this.billingSettings?.max_invoice_discount_percentage ?? 100);
  }

  getItemMaxDiscountPercentage(index: number): number {
    const option = this.getSelectedCatalogOption(index);
    return Number(option?.maxDiscountPercentage ?? this.billingSettings?.max_item_discount_percentage ?? 100);
  }

  getItemMaxDiscountAmount(index: number): number | null {
    const option = this.getSelectedCatalogOption(index);
    const value = option?.maxDiscountAmount ?? this.billingSettings?.max_item_discount_amount ?? null;
    return value === null || value === undefined || value === '' ? null : Number(value);
  }

  onInternalReferralChanged(): void {
    const userId = this.form.getRawValue().internal_referral_user_id;
    if (!this.internalReferralDoctors.find((item) => item.id === userId)) {
      this.form.patchValue({ internal_referral_user_id: '' });
    }
  }

  recalculatePreview(): void {
    const discount = Number(this.form.getRawValue().discount_percentage ?? 0);
    const discountViolation = this.getDiscountLimitViolation();
    if (discountViolation) {
      this.preview = null;
      this.previewMessage = discountViolation;
      return;
    }

    let subTotal = 0;
    let itemDiscountAmount = 0;
    let referredDoctorAmount = 0;
    let selectedLineCount = 0;

    this.items.controls.forEach((_, index) => {
      const option = this.getSelectedCatalogOption(index);
      if (!option) {
        return;
      }
      const raw = this.items.at(index).getRawValue() as { quantity?: number; discount_percentage?: number };
      const quantity = Number(raw.quantity || 0);
      if (quantity <= 0) {
        return;
      }
      selectedLineCount += 1;
      const lineGross = Number(option.unitPrice || 0) * quantity;
      const lineDiscount = (lineGross * Number(raw.discount_percentage || 0)) / 100;
      const lineNet = Math.max(0, lineGross - lineDiscount);
      subTotal += lineNet;
      itemDiscountAmount += lineDiscount;
      referredDoctorAmount += (lineNet * Number(option.doctorSharePercentage || 0)) / 100;
    });

    if (!selectedLineCount) {
      this.preview = null;
      this.previewMessage = '';
      return;
    }

    const invoiceDiscountAmount = (subTotal * discount) / 100;
    const totalAmount = Math.max(0, subTotal - invoiceDiscountAmount);
    this.preview = {
      sub_total: this.toMoney(subTotal),
      item_discount_amount: this.toMoney(itemDiscountAmount),
      discount_percentage: this.toMoney(discount),
      invoice_discount_amount: this.toMoney(invoiceDiscountAmount),
      discount_amount: this.toMoney(itemDiscountAmount + invoiceDiscountAmount),
      total_amount: this.toMoney(totalAmount),
      referred_doctor_amount: this.toMoney(referredDoctorAmount),
    };
    this.previewMessage = '';
  }

  fillFullPayment(): void {
    this.form.patchValue({ payment_amount: this.paymentDuePreview });
    this.persistState();
  }

  openBillingDesk(): void {
    void this.router.navigate(['/billing/list']);
  }

  resetInvoiceDraft(): void {
    this.sourceVisit = null;
    this.sourceAdmission = null;
    this.draft = null;
    this.prefillMessage = '';
    this.selectedPatient = null;
    this.patientLookupControl.setValue('', { emitEvent: false });
    this.form.reset({
      patient_id: '',
      first_name: '',
      last_name: '',
      phone: '',
      email: '',
      gender: '',
      date_of_birth: '',
      address: '',
      internal_referral_user_id: '',
      discount_percentage: 0,
      payment_amount: 0,
      payment_method: 'cash',
      payment_note: '',
      note: '',
    });
    this.items.clear();
    this.addItem();
    this.preview = null;
    this.previewMessage = '';
    this.closePatientSearch();
    this.uiStateService.clear(BillingCreateComponent.STATE_KEY);
  }

  submit(): void {
    this.submitted = true;
    if (this.form.invalid || this.saving) {
      this.form.markAllAsTouched();
      return;
    }

    const value = this.form.getRawValue();
    const items = this.getInvoiceItemsPayload();
    if (!items.length) {
      this.notificationService.warning('Add at least one billing item before posting the invoice.');
      return;
    }
    if (items.some((item) => !this.canUsePayloadItem(item))) {
      this.notificationService.warning('One or more billing items are not allowed for your role.');
      return;
    }
    const discountViolation = this.getDiscountLimitViolation();
    if (discountViolation) {
      this.notificationService.warning(discountViolation);
      return;
    }
    const paymentViolation = this.getPaymentLimitViolation();
    if (paymentViolation) {
      this.notificationService.warning(paymentViolation);
      return;
    }

    this.saving = true;
    const createInvoice = (patientId: string) => {
      const payload: CreateBillingInvoicePayload = {
        patient_id: patientId,
        source_opd_visit_id: this.draft?.source_opd_visit_id || this.sourceVisit?.id || null,
        source_ipd_admission_id: this.draft?.source_ipd_admission_id || this.sourceAdmission?.id || null,
        source_module: this.draft?.source_module || (this.sourceVisit ? 'opd' : this.sourceAdmission ? 'ipd' : null),
        billing_stage: this.draft?.billing_stage || (this.sourceVisit ? 'opd' : this.sourceAdmission ? 'ipd_interim' : null),
        internal_referral_user_id: value.internal_referral_user_id || null,
        discount_percentage: Number(value.discount_percentage ?? 0),
        note: value.note || null,
        items,
      };

      this.billingService.createInvoice(payload).subscribe({
        next: (invoice) => {
          const finalizeNavigation = (postedInvoice: BillingInvoice) => {
            this.saving = false;
            this.submitted = false;
            this.clearDraftKeepContext();
            this.printInvestigationStickers(postedInvoice);
            this.notificationService.success(`Invoice ${postedInvoice.invoice_number} created successfully.`);
            const hasDue = Number(postedInvoice.due_amount || 0) > 0;
            void this.router.navigate([hasDue ? '/billing/due-payments' : '/billing/list'], {
              queryParams: { invoiceId: postedInvoice.id, printInvoice: '1' },
            });
          };

          const collectInitialPayment = () => {
            const paymentAmount = Number(this.form.getRawValue().payment_amount || 0);
            if (paymentAmount <= 0) {
              finalizeNavigation(invoice);
              return;
            }
            this.billingService.collectPayment(invoice.id, {
              amount: paymentAmount,
              payment_method: (this.form.getRawValue().payment_method || 'cash') as 'cash' | 'card' | 'mobile_banking' | 'bank_transfer',
              note: this.form.getRawValue().payment_note || null,
            }).subscribe({
              next: (paidInvoice) => finalizeNavigation(paidInvoice),
              error: () => {
                this.saving = false;
                this.notificationService.warning(`Invoice ${invoice.invoice_number} posted, but payment collection failed. Collect it from due payments.`);
              },
            });
          };

          if (this.sourceVisit) {
            this.opdService.updateStatus(this.sourceVisit.id, 'billed').subscribe({
              next: () => {
                this.prefillMessage = `${this.sourceVisit?.visit_number} billed and synced back to OPD.`;
                collectInitialPayment();
              },
              error: () => {
                this.saving = false;
                this.notificationService.warning(`Invoice ${invoice.invoice_number} posted, but OPD status was not updated.`);
              },
            });
            return;
          }

          collectInitialPayment();
        },
        error: () => {
          this.saving = false;
        },
      });
    };

    if (value.patient_id) {
      createInvoice(value.patient_id);
      return;
    }

    const patientPayload: CreatePatientPayload = {
      first_name: value.first_name ?? '',
      last_name: value.last_name ?? '',
      phone: value.phone || null,
      email: value.email || null,
      gender: value.gender || null,
      date_of_birth: value.date_of_birth || null,
      address: value.address || null,
    };

    this.patientService.create(patientPayload).subscribe({
      next: (patient) => {
        this.selectedPatient = patient;
        this.form.patchValue({ patient_id: patient.id }, { emitEvent: false });
        this.patientLookupControl.setValue(`${patient.patient_number} - ${patient.first_name} ${patient.last_name}`, {
          emitEvent: false,
        });
        createInvoice(patient.id);
      },
      error: () => {
        this.saving = false;
      },
    });
  }

  formatPatient(patient: Patient): string {
    return `${patient.patient_number} - ${patient.first_name} ${patient.last_name}`;
  }

  formatPatientLookupMeta(patient: PatientLookupResult): string {
    return [patient.phone || 'No phone', patient.email || 'No email', patient.gender || 'No gender'].join(' · ');
  }

  getServiceName(serviceId: string): string {
    return this.billingServices.find((service) => service.id === serviceId)?.name ?? 'Select service';
  }

  getServiceCode(serviceId: string): string {
    return this.billingServices.find((service) => service.id === serviceId)?.service_code ?? '--';
  }

  getServiceUnitPrice(serviceId: string): string {
    return this.formatCurrency(this.billingServices.find((service) => service.id === serviceId)?.unit_price ?? 0);
  }

  getCatalogCode(index: number): string {
    return this.getSelectedCatalogOption(index)?.code ?? '--';
  }

  getCatalogUnitPrice(index: number): string {
    return this.formatCurrency(this.getSelectedCatalogOption(index)?.unitPrice ?? 0);
  }

  getItemDiscountAmount(serviceId: string, quantity: number, discountPercentage: number): string {
    const unitPrice = this.billingServices.find((item) => item.id === serviceId)?.unit_price;
    if (!unitPrice) {
      return this.formatCurrency(0);
    }
    const gross = Number(unitPrice) * Number(quantity || 0);
    return this.formatCurrency((gross * Number(discountPercentage || 0)) / 100);
  }

  getServiceAmount(serviceId: string, quantity: number, discountPercentage = 0): string {
    const unitPrice = this.billingServices.find((item) => item.id === serviceId)?.unit_price;
    if (!unitPrice) {
      return this.formatCurrency(0);
    }
    const gross = Number(unitPrice) * Number(quantity || 0);
    const discount = (gross * Number(discountPercentage || 0)) / 100;
    return this.formatCurrency(gross - discount);
  }

  getCatalogDiscountAmount(index: number, quantity: number, discountPercentage: number): string {
    const gross = Number(this.getSelectedCatalogOption(index)?.unitPrice ?? 0) * Number(quantity || 0);
    return this.formatCurrency((gross * Number(discountPercentage || 0)) / 100);
  }

  getCatalogAmount(index: number, quantity: number, discountPercentage = 0): string {
    const gross = Number(this.getSelectedCatalogOption(index)?.unitPrice ?? 0) * Number(quantity || 0);
    const discount = (gross * Number(discountPercentage || 0)) / 100;
    return this.formatCurrency(gross - discount);
  }

  formatCurrency(value: string | number): string {
    return new Intl.NumberFormat('en-BD', {
      style: 'currency',
      currency: 'BDT',
      minimumFractionDigits: 2,
    }).format(Number(value));
  }

  private toMoney(value: number): string {
    return Number(value || 0).toFixed(2);
  }

  private bindPatientSearch(): void {
    this.patientLookupControl.valueChanges.pipe(debounceTime(400), distinctUntilChanged()).subscribe((value) => {
      this.searchPatients(value, 'lookup');
    });

    this.form.controls.phone.valueChanges.pipe(debounceTime(400), distinctUntilChanged()).subscribe((value) => {
      if (!this.hasExistingPatientSelection) {
        this.searchPatients(value ?? '', 'phone');
      }
    });

    this.form.controls.email.valueChanges.pipe(debounceTime(400), distinctUntilChanged()).subscribe((value) => {
      if (!this.hasExistingPatientSelection) {
        this.searchPatients(value ?? '', 'email');
      }
    });
  }

  private getInvoiceItemsPayload(): BillingInvoiceItemPayload[] {
    const rawItems = this.items.getRawValue() as {
      billing_service_id?: string;
      source_item_type?: BillingCatalogType;
      source_item_id?: string;
      quantity?: number;
      discount_percentage?: number;
      source_opd_visit_order_id?: string;
      source_label?: string;
      source_module?: string;
    }[];
    return rawItems
      .filter((item) => (item.billing_service_id || item.source_item_id) && Number(item.quantity) > 0)
      .map((item) => ({
        billing_service_id: item.billing_service_id || null,
        quantity: Number(item.quantity),
        discount_percentage: Number(item.discount_percentage ?? 0),
        source_opd_visit_order_id: item.source_opd_visit_order_id || null,
        source_label: item.source_label || null,
        source_module: item.source_module || null,
        source_item_type: item.source_item_type || (item.billing_service_id ? 'billing_service' : null),
        source_item_id: item.source_item_id || item.billing_service_id || null,
      }));
  }

  getSelectedCatalogOption(index: number): BillingCatalogOption | null {
    const item = this.items.at(index);
    const sourceType = item.get('source_item_type')?.value as BillingCatalogType | null;
    const sourceId = item.get('source_item_id')?.value || item.get('billing_service_id')?.value;
    return this.billingCatalogOptions.find((option) => option.type === sourceType && option.id === sourceId) ?? null;
  }

  private getDiscountLimitViolation(): string | null {
    const invoiceDiscount = Number(this.form.getRawValue().discount_percentage ?? 0);
    if (invoiceDiscount > this.maxInvoiceDiscountPercentage) {
      return `Invoice discount cannot exceed ${this.maxInvoiceDiscountPercentage}%.`;
    }
    const subtotal = this.items.controls.reduce((total, item, index) => {
      const option = this.getSelectedCatalogOption(index);
      if (!option) {
        return total;
      }
      const quantity = Number(item.get('quantity')?.value ?? 0);
      const discount = Number(item.get('discount_percentage')?.value ?? 0);
      const gross = Number(option.unitPrice || 0) * quantity;
      return total + Math.max(0, gross - (gross * discount) / 100);
    }, 0);
    const invoiceDiscountAmount = (subtotal * invoiceDiscount) / 100;
    const invoiceAmountCap = this.billingSettings?.max_invoice_discount_amount;
    if (invoiceAmountCap !== null && invoiceAmountCap !== undefined && invoiceAmountCap !== '' && invoiceDiscountAmount > Number(invoiceAmountCap)) {
      return `Invoice discount amount cannot exceed ${this.formatCurrency(invoiceAmountCap)}.`;
    }
    const itemOverLimitIndex = this.items.controls.findIndex((item, index) => Number(item.get('discount_percentage')?.value ?? 0) > this.getItemMaxDiscountPercentage(index));
    if (itemOverLimitIndex >= 0) {
      return `Item discount cannot exceed ${this.getItemMaxDiscountPercentage(itemOverLimitIndex)}%.`;
    }
    const itemAmountOverLimitIndex = this.items.controls.findIndex((item, index) => {
      const cap = this.getItemMaxDiscountAmount(index);
      const option = this.getSelectedCatalogOption(index);
      if (cap === null || !option) {
        return false;
      }
      const gross = Number(option.unitPrice || 0) * Number(item.get('quantity')?.value ?? 0);
      const discountAmount = (gross * Number(item.get('discount_percentage')?.value ?? 0)) / 100;
      return discountAmount > cap;
    });
    if (itemAmountOverLimitIndex >= 0) {
      return `Item discount amount cannot exceed ${this.formatCurrency(this.getItemMaxDiscountAmount(itemAmountOverLimitIndex) ?? 0)}.`;
    }
    return null;
  }

  private getPaymentLimitViolation(): string | null {
    const paymentAmount = Number(this.form.getRawValue().payment_amount ?? 0);
    if (paymentAmount < 0) {
      return 'Payment amount cannot be negative.';
    }
    if (this.preview && paymentAmount > Number(this.preview.total_amount)) {
      return `Payment amount cannot exceed ${this.formatCurrency(this.preview.total_amount)}.`;
    }
    return null;
  }

  private isInvestigationModule(module?: string | null): boolean {
    return ['laboratory', 'radiology', 'opd_investigation'].includes(String(module || '').toLowerCase());
  }

  private printInvestigationStickers(invoice: BillingInvoice): void {
    const stickers = invoice.items.filter((item) => this.isInvestigationModule(item.source_module));
    if (!stickers.length) {
      return;
    }
    const patientName = `${invoice.patient.first_name} ${invoice.patient.last_name}`.trim();
    const printed = printInvestigationStickers(
      stickers.map((item, index) => {
        const token = item.source_opd_visit_order_id ? String(item.source_opd_visit_order_id).slice(0, 8).toUpperCase() : `${invoice.invoice_number}-${index + 1}`;
        return {
          module: String(item.source_module || 'Investigation').toUpperCase(),
          token,
          patientNumber: invoice.patient.patient_number,
          patientName,
          invoiceNumber: invoice.invoice_number,
          testName: item.service_name,
          roomNumber: item.room_number,
          quantity: item.quantity,
        };
      }),
      `Investigation Stickers - ${invoice.invoice_number}`
    );
    if (!printed) {
      this.notificationService.warning('Popup blocked. Allow popups to print investigation stickers.');
    }
  }

  private restoreState(): void {
    const state = this.uiStateService.load<{
      patient_id?: string;
      first_name?: string;
      last_name?: string;
      phone?: string;
      email?: string;
      gender?: string;
      date_of_birth?: string;
      address?: string;
      internal_referral_user_id?: string;
      discount_percentage?: number;
      payment_amount?: number;
      payment_method?: string;
      payment_note?: string;
      note?: string;
      items?: BillingInvoiceItemPayload[];
    }>(BillingCreateComponent.STATE_KEY);

    if (!state) {
      return;
    }

    this.form.patchValue({
      patient_id: state.patient_id ?? '',
      first_name: state.first_name ?? '',
      last_name: state.last_name ?? '',
      phone: state.phone ?? '',
      email: state.email ?? '',
      gender: state.gender ?? '',
      date_of_birth: state.date_of_birth ?? '',
      address: state.address ?? '',
      internal_referral_user_id: state.internal_referral_user_id ?? '',
      discount_percentage: state.discount_percentage ?? 0,
      payment_amount: state.payment_amount ?? 0,
      payment_method: state.payment_method ?? 'cash',
      payment_note: state.payment_note ?? '',
      note: state.note ?? '',
    });

    this.items.clear();
    for (const item of state.items ?? []) {
        this.items.push(
          this.fb.group({
            billing_service_id: [item.billing_service_id || ''],
            catalog_search: [item.source_label || ''],
            source_item_type: [item.source_item_type || 'billing_service'],
            source_item_id: [item.source_item_id || item.billing_service_id || ''],
            quantity: [item.quantity, [Validators.required, Validators.min(0.01)]],
            discount_percentage: [item.discount_percentage ?? 0, [Validators.min(0), Validators.max(100)]],
            source_opd_visit_order_id: [item.source_opd_visit_order_id || ''],
            source_label: [item.source_label || ''],
            source_module: [item.source_module || ''],
          })
        );
    }
  }

  private persistState(): void {
    const value = this.form.getRawValue();
    this.uiStateService.save(BillingCreateComponent.STATE_KEY, {
      patient_id: value.patient_id ?? '',
      first_name: value.first_name ?? '',
      last_name: value.last_name ?? '',
      phone: value.phone ?? '',
      email: value.email ?? '',
      gender: value.gender ?? '',
      date_of_birth: value.date_of_birth ?? '',
      address: value.address ?? '',
      internal_referral_user_id: value.internal_referral_user_id ?? '',
      discount_percentage: Number(value.discount_percentage ?? 0),
      payment_amount: Number(value.payment_amount ?? 0),
      payment_method: value.payment_method ?? 'cash',
      payment_note: value.payment_note ?? '',
      note: value.note ?? '',
      items: this.getInvoiceItemsPayload(),
    });
  }

  private clearDraftKeepContext(): void {
    const value = this.form.getRawValue();
    this.form.reset({
      patient_id: value.patient_id ?? '',
      first_name: value.first_name ?? '',
      last_name: value.last_name ?? '',
      phone: value.phone ?? '',
      email: value.email ?? '',
      gender: value.gender ?? '',
      date_of_birth: value.date_of_birth ?? '',
      address: value.address ?? '',
      internal_referral_user_id: '',
      discount_percentage: 0,
      payment_amount: 0,
      payment_method: 'cash',
      payment_note: '',
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
    const matchedPatient = this.patients.find((item) => item.id === patientId) ?? null;
    if (!matchedPatient) {
      this.selectedPatient = patientId ? this.selectedPatient : null;
      return;
    }
    this.patchPatientDetails(matchedPatient);
  }

  private patchPatientDetails(patient: Patient): void {
    this.form.patchValue(
      {
        patient_id: patient.id,
        first_name: patient.first_name,
        last_name: patient.last_name,
        phone: patient.phone || '',
        email: patient.email || '',
        gender: patient.gender || '',
        date_of_birth: patient.date_of_birth || '',
        address: patient.address || '',
      },
      { emitEvent: false }
    );
    this.selectedPatient = patient;
    this.patientLookupControl.setValue(`${patient.patient_number} - ${patient.first_name} ${patient.last_name}`, {
      emitEvent: false,
    });
  }

  private loadVisitPrefill(visitId: string): void {
    this.opdService.getVisit(visitId).subscribe((visit) => {
      this.sourceVisit = visit;
      this.sourceAdmission = null;
      this.draft = null;
      this.patchPatientDetails(visit.patient);

      const referralDoctor = visit.consulting_doctor_user_id
        ? this.internalReferralDoctors.find((item) => item.id === visit.consulting_doctor_user_id)
        : null;
      if (referralDoctor) {
        this.form.patchValue({ internal_referral_user_id: referralDoctor.id });
      }

      this.billingService.getOpdDraft(visitId).subscribe({
        next: (draft) => {
          this.applyDraft(draft);
        },
        error: () => {
          this.form.patchValue({ note: this.buildVisitNote(visit) });
          this.applyVisitServiceSuggestion(visit);
          this.recalculatePreview();
          this.persistState();
        },
      });
    });
  }

  private loadAdmissionPrefill(admissionId: string, stage: 'interim' | 'final'): void {
    this.ipdService.getAdmission(admissionId).subscribe((admission) => {
      this.sourceAdmission = admission;
      this.sourceVisit = null;
      this.draft = null;
      this.patchPatientDetails(admission.patient);

      const referralDoctor = admission.attending_doctor_user_id
        ? this.internalReferralDoctors.find((item) => item.id === admission.attending_doctor_user_id)
        : null;
      if (referralDoctor) {
        this.form.patchValue({ internal_referral_user_id: referralDoctor.id });
      }

      this.billingService.getIpdDraft(admissionId, stage).subscribe({
        next: (draft) => {
          this.applyDraft(draft);
        },
        error: () => {
          this.form.patchValue({ note: this.buildAdmissionNote(admission) });
          this.prefillMessage = `Loaded ${admission.admission_number} for ${stage} billing handoff.`;
          this.recalculatePreview();
          this.persistState();
        },
      });
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
          billing_service_id: [matchedService.id],
          catalog_search: [`Billing Service - ${matchedService.name}`],
          source_item_type: ['billing_service'],
          source_item_id: [matchedService.id],
          quantity: [1, [Validators.required, Validators.min(0.01)]],
          discount_percentage: [0, [Validators.min(0), Validators.max(100)]],
          source_opd_visit_order_id: [''],
          source_label: [`Billing Service · ${matchedService.name}`],
          source_module: ['billing'],
        })
      );
      this.prefillMessage = `Loaded ${visit.visit_number} and matched consultation billing service ${matchedService.service_code}.`;
      return;
    }

    this.prefillMessage = `Loaded ${visit.visit_number}. No consultation billing service matched ${this.formatCurrency(visit.consultation_fee)} automatically.`;
  }

  private applyDraft(draft: BillingDraft): void {
    this.draft = draft;
    this.items.clear();
    for (const item of draft.items) {
      this.items.push(
        this.fb.group({
          billing_service_id: [item.billing_service_id || ''],
          catalog_search: [item.source_label || item.billing_service_name || ''],
          source_item_type: [item.source_item_type || 'billing_service'],
          source_item_id: [item.source_item_id || item.billing_service_id || ''],
          quantity: [Number(item.quantity), [Validators.required, Validators.min(0.01)]],
          discount_percentage: [Number(item.discount_percentage || 0), [Validators.min(0), Validators.max(100)]],
          source_opd_visit_order_id: [item.source_opd_visit_order_id || ''],
          source_label: [item.source_label || ''],
          source_module: [item.source_module || ''],
        })
      );
    }
    if (!draft.items.length) {
      this.addItem();
    }
    this.form.patchValue({
      patient_id: draft.patient_id,
      internal_referral_user_id: draft.internal_referral_user_id || this.form.getRawValue().internal_referral_user_id,
      note: draft.note || this.form.getRawValue().note,
    });
    this.prefillMessage = draft.message || 'Draft applied.';
    this.recalculatePreview();
    this.persistState();
  }
}
