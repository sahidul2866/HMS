import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { PERMISSIONS } from '../../../../core/constants/permissions';
import { User } from '../../../../core/models/auth.models';
import { DoctorDirectoryService } from '../../../../core/services/doctor-directory.service';
import { SessionService } from '../../../../core/services/session.service';
import { NotificationService } from '../../../../core/services/notification.service';
import { ConfigurationProfile, ConfigurationService } from '../../../configuration/services/configuration.service';
import { PharmacyInvestigationSetting, PharmacyMedicine } from '../../../pharmacy/models/pharmacy.models';
import { PharmacyService } from '../../../pharmacy/services/pharmacy.service';
import { printOPDPrescription } from '../../../../shared/utils/opd-prescription-printer';
import { OPDVisit, OPDVisitOrder } from '../../models/opd.models';
import { OPDService } from '../../services/opd.service';

type PrescriptionPlacement = 'full' | 'left' | 'right';

type PrescriptionSectionView = {
  key: string;
  label: string;
  placement: PrescriptionPlacement;
  height: number;
};

type MedicineDraft = {
  item_name: string;
  strength: string;
  dosage: string;
  frequency: string;
  duration: string;
  route: string;
  timing: string;
  instructions: string;
  quantity: number;
};

type InvestigationDraft = {
  item_name: string;
  service_area: string;
  instructions: string;
};

type PrescriptionTemplate = {
  name: string;
  complaint: string;
  diagnosis: string;
  medicines: Array<Partial<MedicineDraft> & { name: string }>;
  investigations: Array<{ name: string; service_area: string }>;
  advice: string[];
};

const DEFAULT_PRESCRIPTION_SECTIONS: PrescriptionSectionView[] = [
  { key: 'complaint', label: 'Chief Complaint', placement: 'left', height: 92 },
  { key: 'history', label: 'History', placement: 'left', height: 94 },
  { key: 'vitals', label: 'Vitals', placement: 'left', height: 72 },
  { key: 'examination', label: 'Examination', placement: 'left', height: 100 },
  { key: 'diagnosis', label: 'Diagnosis', placement: 'left', height: 82 },
  { key: 'rx', label: 'Rx', placement: 'right', height: 210 },
  { key: 'investigation', label: 'Investigations', placement: 'right', height: 78 },
  { key: 'advice', label: 'Advice', placement: 'right', height: 86 },
  { key: 'follow_up', label: 'Follow-Up', placement: 'right', height: 54 },
];

@Component({
  selector: 'app-opd-visit-list',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './opd-visit-list.component.html',
  styleUrls: ['./opd-visit-list.component.scss'],
})
export class OPDVisitListComponent {
  private readonly opdService = inject(OPDService);
  private readonly pharmacyService = inject(PharmacyService);
  private readonly doctorDirectoryService = inject(DoctorDirectoryService);
  private readonly configurationService = inject(ConfigurationService);
  private readonly notificationService = inject(NotificationService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  readonly session = inject(SessionService);
  readonly permissions = PERMISSIONS;

  visits: OPDVisit[] = [];
  doctors: User[] = [];
  configurationProfiles: ConfigurationProfile[] = [];
  selectedDoctorUserId = '';
  searchText = '';
  selectedStatus = '';
  selectedPayment = '';
  selectedDate = '';
  selectedVisit: OPDVisit | null = null;
  previousVisits: OPDVisit[] = [];
  pharmacyMedicines: PharmacyMedicine[] = [];
  investigationSettings: PharmacyInvestigationSetting[] = [];
  savingConsultation = false;
  savingOrder = false;
  editingOrderId = '';
  medicineSearch = '';
  investigationSearch = '';
  diagnosisSearch = '';
  adviceSearch = '';
  medicineSuggestionsLoading = false;
  investigationSuggestionsLoading = false;
  private medicineSearchTimer: ReturnType<typeof setTimeout> | null = null;
  private investigationSearchTimer: ReturnType<typeof setTimeout> | null = null;
  private medicineSearchToken = 0;
  private investigationSearchToken = 0;
  prescriptionDraft = {
    chief_complaint: '',
    history_of_present_illness: '',
    vital_signs: '',
    examination_note: '',
    provisional_diagnosis: '',
    final_diagnosis: '',
    follow_up_date: '',
    follow_up_note: '',
    item_name: '',
    instructions: '',
    quantity: 1,
  };
  medicineDraft: MedicineDraft = this.emptyMedicineDraft();
  investigationDraft: InvestigationDraft = this.emptyInvestigationDraft();
  page = 1;
  pageSize = 12;
  sortField: 'visit_number' | 'patient' | 'department' | 'doctor' | 'fee' | 'payment' | 'status' = 'visit_number';
  sortDirection: 'asc' | 'desc' = 'desc';

  constructor() {
    this.doctorDirectoryService.listDoctors().subscribe((doctors) => (this.doctors = doctors));
    this.configurationService.workspace().subscribe((workspace) => (this.configurationProfiles = workspace.profiles));
    this.loadPrescriptionCatalog();
    this.loadVisits();
    this.route.queryParamMap.subscribe((params) => {
      const openVisit = params.get('openVisit');
      if (openVisit) {
        this.openVisit(openVisit);
      }
    });
  }

  loadVisits(): void {
    const doctorUserId = this.selectedDoctorUserId || null;
    this.opdService.listVisits(doctorUserId).subscribe((visits) => (this.visits = visits));
  }

  openVisit(visitId: string): void {
    this.opdService.getVisit(visitId).subscribe((visit) => {
      this.setSelectedVisit(visit);
      this.applyVisitToPrescriptionDraft(visit);
      this.loadPreviousVisits(visit);
    });
  }

  closeVisit(): void {
    this.selectedVisit = null;
  }

  navigateToRegisterVisit(): void {
    void this.router.navigate(['/opd/register']);
  }

  navigateToNewPatient(): void {
    void this.router.navigate(['/patients/new'], { queryParams: { returnTo: '/opd/register' } });
  }

  startVisit(visit: OPDVisit): void {
    if (!this.canStartVisit) return;
    void this.router.navigate(['/opd'], { queryParams: { openVisit: visit.id } });
  }

  openPayment(visit: OPDVisit): void {
    if (!this.session.hasPermission(PERMISSIONS.billingPaymentCollect)) return;
    void this.router.navigate(['/billing/create'], { queryParams: { opdVisitId: visit.id } });
  }

  convertToIpd(visit: OPDVisit): void {
    if (!this.session.hasPermission(PERMISSIONS.ipdAdmissionManage)) return;
    const clinicalContext = [
      visit.chief_complaint ? `Chief complaint: ${visit.chief_complaint}` : '',
      visit.history_of_present_illness ? `History: ${visit.history_of_present_illness}` : '',
      visit.vital_signs ? `Vitals: ${visit.vital_signs}` : '',
      visit.examination_note ? `Examination: ${visit.examination_note}` : '',
    ].filter(Boolean).join('\n');
    void this.router.navigate(['/ipd/admit'], {
      queryParams: {
        patientId: visit.patient.id,
        sourceOpdVisitId: visit.id,
        sourceOpdVisitNumber: visit.visit_number,
        departmentName: visit.department_name,
        doctorUserId: visit.consulting_doctor_user_id || visit.doctor_user_id || null,
        attendingDoctorName: visit.consulting_doctor_name,
        diagnosis: visit.final_diagnosis || visit.provisional_diagnosis || visit.chief_complaint || '',
        clinicalContext,
      },
    });
  }

  isPaymentDone(visit: OPDVisit): boolean {
    return (visit.consultation_payment_status || '').toLowerCase() === 'paid';
  }

  formatCurrency(value: string | number | null | undefined): string {
    return `BDT ${Number(value || 0).toFixed(2)}`;
  }

  get filteredVisits(): OPDVisit[] {
    const search = this.searchText.trim().toLowerCase();
    return this.visits.filter((visit) => {
      const statusMatch = !this.selectedStatus || visit.status === this.selectedStatus;
      const paymentStatus = (visit.consultation_payment_status || 'unpaid').toLowerCase();
      const paymentMatch = !this.selectedPayment || paymentStatus === this.selectedPayment;
      const dateMatch = !this.selectedDate || visit.visit_date === this.selectedDate;
      const searchMatch =
        !search ||
        visit.visit_number.toLowerCase().includes(search) ||
        `${visit.patient.first_name} ${visit.patient.last_name}`.toLowerCase().includes(search) ||
        visit.patient.patient_number.toLowerCase().includes(search) ||
        (visit.consulting_doctor_name || '').toLowerCase().includes(search) ||
        (visit.department_name || '').toLowerCase().includes(search);
      return statusMatch && paymentMatch && dateMatch && searchMatch;
    });
  }

  get sortedVisits(): OPDVisit[] {
    const dir = this.sortDirection === 'asc' ? 1 : -1;
    return [...this.filteredVisits].sort((a, b) => {
      switch (this.sortField) {
        case 'patient':
          return dir * `${a.patient.first_name} ${a.patient.last_name}`.localeCompare(`${b.patient.first_name} ${b.patient.last_name}`);
        case 'department':
          return dir * (a.department_name || '').localeCompare(b.department_name || '');
        case 'doctor':
          return dir * (a.consulting_doctor_name || '').localeCompare(b.consulting_doctor_name || '');
        case 'fee':
          return dir * (Number(a.consultation_fee || 0) - Number(b.consultation_fee || 0));
        case 'payment':
          return dir * (Number(a.consultation_total || a.consultation_fee || 0) - Number(b.consultation_total || b.consultation_fee || 0));
        case 'status':
          return dir * (a.status || '').localeCompare(b.status || '');
        case 'visit_number':
        default:
          return dir * (a.visit_number || '').localeCompare(b.visit_number || '');
      }
    });
  }

  get displayedVisits(): OPDVisit[] {
    const start = (this.page - 1) * this.pageSize;
    return this.sortedVisits.slice(start, start + this.pageSize);
  }

  get totalPages(): number {
    return Math.max(Math.ceil(this.filteredVisits.length / this.pageSize), 1);
  }

  get rangeStart(): number {
    return this.filteredVisits.length ? (this.page - 1) * this.pageSize + 1 : 0;
  }

  get rangeEnd(): number {
    return Math.min(this.page * this.pageSize, this.filteredVisits.length);
  }

  onFiltersChanged(): void {
    this.page = 1;
  }

  toggleSort(field: OPDVisitListComponent['sortField']): void {
    if (this.sortField === field) {
      this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
      this.page = 1;
      return;
    }
    this.sortField = field;
    this.sortDirection = field === 'visit_number' ? 'desc' : 'asc';
    this.page = 1;
  }

  sortClass(field: OPDVisitListComponent['sortField']): string {
    return this.sortField === field ? `sorted-${this.sortDirection}` : '';
  }

  previousPage(): void {
    this.page = Math.max(this.page - 1, 1);
  }

  nextPage(): void {
    this.page = Math.min(this.page + 1, this.totalPages);
  }

  get canFilterByDoctor(): boolean {
    return this.session.hasPermission(PERMISSIONS.opdViewDoctorWise);
  }

  get canStartVisit(): boolean {
    const user = this.session.snapshot.user;
    return !!user?.roles?.some((role) => role.is_doctor_role || role.code === 'DOCTOR');
  }

  get activeLayoutProfile(): ConfigurationProfile | null {
    return this.findProfile('prescription_layout', this.selectedVisit);
  }

  get activeSuggestionProfile(): ConfigurationProfile | null {
    return this.findProfile('prescription_suggestion', this.selectedVisit);
  }

  get prescriptionSections(): string[] {
    return this.prescriptionLayoutSections.map((section) => section.key);
  }

  get prescriptionLayoutSections(): PrescriptionSectionView[] {
    return this.normalizePrescriptionSections(this.activeLayoutProfile?.payload || {});
  }

  get fullPrescriptionSections(): PrescriptionSectionView[] {
    return this.prescriptionLayoutSections.filter((section) => section.placement === 'full');
  }

  get leftPrescriptionSections(): PrescriptionSectionView[] {
    return this.prescriptionLayoutSections.filter((section) => section.placement === 'left');
  }

  get rightPrescriptionSections(): PrescriptionSectionView[] {
    return this.prescriptionLayoutSections.filter((section) => section.placement === 'right');
  }

  get prescriptionLeftColumnWidth(): number {
    return this.normalizeColumnWidth(this.activeLayoutProfile?.payload?.['left_column_width']);
  }

  get prescriptionRightColumnWidth(): number {
    return 100 - this.prescriptionLeftColumnWidth;
  }

  get prescriptionGridColumns(): string {
    return `${this.prescriptionLeftColumnWidth}fr ${this.prescriptionRightColumnWidth}fr`;
  }

  get medicineSuggestions(): string[] {
    return this.profileList(this.activeSuggestionProfile, 'medicines');
  }

  get complaintSuggestions(): string[] {
    return this.profileList(this.activeSuggestionProfile, 'complaints');
  }

  get diagnosisSuggestions(): string[] {
    return this.profileList(this.activeSuggestionProfile, 'diagnoses');
  }

  get adviceSuggestions(): string[] {
    return this.profileList(this.activeSuggestionProfile, 'advice');
  }

  get activePrescriptionOrders(): OPDVisitOrder[] {
    return this.activeOrders('prescription');
  }

  get activeInvestigationOrders(): OPDVisitOrder[] {
    return this.activeOrders('investigation');
  }

  get dosageOptions(): string[] {
    return ['1 tab', '1/2 tab', '2 tab', '5 ml', '10 ml', '1 puff', '1 drop'];
  }

  get frequencyOptions(): string[] {
    return ['1+0+1', '1+1+1', '1+0+0', '0+1+0', '0+0+1', '1+1+0', '0+1+1', 'SOS'];
  }

  get timingOptions(): string[] {
    return ['After meal', 'Before meal', 'With meal', 'At bedtime', 'Morning', 'Evening'];
  }

  get routeOptions(): string[] {
    return ['Oral', 'Topical', 'Inhalation', 'Nasal', 'Eye', 'Ear', 'IM', 'IV'];
  }

  get quickTemplates(): PrescriptionTemplate[] {
    return [
      { name: 'Fever', complaint: 'Fever with body ache', diagnosis: 'Acute febrile illness', medicines: [{ name: 'Paracetamol', dosage: '1 tab', frequency: '1+1+1', duration: '3 days', timing: 'After meal' }], investigations: [{ name: 'CBC', service_area: 'laboratory' }], advice: ['Take adequate fluid', 'Tepid sponging if high fever'] },
      { name: 'Diabetes F/U', complaint: 'Diabetes follow-up', diagnosis: 'Type 2 diabetes mellitus', medicines: [], investigations: [{ name: 'Fasting Blood Sugar', service_area: 'laboratory' }, { name: 'HbA1c', service_area: 'laboratory' }], advice: ['Continue diabetic diet', 'Regular walking 30 minutes daily'] },
      { name: 'Hypertension F/U', complaint: 'Hypertension follow-up', diagnosis: 'Hypertension', medicines: [], investigations: [{ name: 'Serum Creatinine', service_area: 'laboratory' }, { name: 'ECG', service_area: 'laboratory' }], advice: ['Low salt diet', 'Monitor blood pressure regularly'] },
      { name: 'Cold/Cough', complaint: 'Runny nose and cough', diagnosis: 'Upper respiratory tract infection', medicines: [{ name: 'Cetirizine', dosage: '1 tab', frequency: '0+0+1', duration: '5 days', timing: 'At bedtime' }], investigations: [], advice: ['Steam inhalation', 'Avoid cold drinks'] },
      { name: 'Abdominal Pain', complaint: 'Abdominal pain', diagnosis: 'Abdominal pain under evaluation', medicines: [], investigations: [{ name: 'CBC', service_area: 'laboratory' }, { name: 'USG Whole Abdomen', service_area: 'radiology' }], advice: ['Return urgently if pain increases or vomiting persists'] },
    ];
  }

  get filteredMedicineSuggestions(): PharmacyMedicine[] {
    const query = [this.medicineSearch, this.medicineDraft.item_name, this.prescriptionDraft.final_diagnosis, this.prescriptionDraft.provisional_diagnosis].join(' ').trim().toLowerCase();
    const favorites = new Set(this.medicineSuggestions.map((item) => item.toLowerCase()));
    const pool = [...this.pharmacyMedicines].sort((a, b) => {
      const favoriteSort = (favorites.has(a.name.toLowerCase()) ? 0 : 1) - (favorites.has(b.name.toLowerCase()) ? 0 : 1);
      return favoriteSort || Number(b.stock_quantity || 0) - Number(a.stock_quantity || 0);
    });
    if (!query) return pool.slice(0, 8);
    return pool.filter((medicine) => [medicine.name, medicine.generic_name, medicine.strength, medicine.dosage_form, medicine.description].filter(Boolean).join(' ').toLowerCase().includes(query)).slice(0, 8);
  }

  get filteredInvestigationSuggestions(): PharmacyInvestigationSetting[] {
    const query = [this.investigationSearch, this.investigationDraft.item_name, this.prescriptionDraft.final_diagnosis, this.prescriptionDraft.chief_complaint].join(' ').trim().toLowerCase();
    const pool = this.investigationSettings.filter((item) => item.is_active !== false);
    if (!query) return pool.slice(0, 10);
    return pool.filter((item) => [item.test_name, item.category_name, item.service_area, item.description, item.code].filter(Boolean).join(' ').toLowerCase().includes(query)).slice(0, 10);
  }

  get diagnosisQuickSuggestions(): string[] {
    return this.filterTextSuggestions(this.diagnosisSuggestions, this.diagnosisSearch || this.prescriptionDraft.final_diagnosis).slice(0, 8);
  }

  get adviceQuickSuggestions(): string[] {
    return this.filterTextSuggestions(this.adviceSuggestions, this.adviceSearch || this.prescriptionDraft.follow_up_note).slice(0, 8);
  }

  sectionLabel(section: string): string {
    const labels: Record<string, string> = {
      header: 'Doctor Header',
      patient: 'Patient Details',
      vitals: 'Vitals',
      complaint: 'Chief Complaint',
      history: 'History',
      examination: 'Examination',
      diagnosis: 'Diagnosis',
      rx: 'Medicines',
      investigation: 'Investigations',
      advice: 'Advice',
      follow_up: 'Follow-Up',
      signature: 'Signature',
    };
    return labels[section] || section;
  }

  applySuggestion(field: 'chief_complaint' | 'final_diagnosis' | 'instructions' | 'item_name', value: string): void {
    if (field === 'instructions' && this.prescriptionDraft.instructions) {
      this.prescriptionDraft.instructions = `${this.prescriptionDraft.instructions}\n${value}`;
      return;
    }
    this.prescriptionDraft[field] = value;
  }

  onMedicineQueryChanged(query: string): void {
    this.medicineSearch = query;
    if (this.medicineSearchTimer) window.clearTimeout(this.medicineSearchTimer);
    const normalized = query.trim();
    if (normalized.length < 2) return;
    this.medicineSearchTimer = window.setTimeout(() => this.searchMedicineCatalog(normalized), 160);
  }

  onInvestigationQueryChanged(query: string): void {
    this.investigationSearch = query;
    if (this.investigationSearchTimer) window.clearTimeout(this.investigationSearchTimer);
    const normalized = query.trim();
    if (normalized.length < 2) return;
    this.investigationSearchTimer = window.setTimeout(() => this.searchInvestigationCatalog(normalized), 160);
  }

  addBestMedicineFromKeyboard(): void {
    const bestMatch = this.filteredMedicineSuggestions[0];
    if (bestMatch && this.medicineDraft.item_name.trim().length >= 2) {
      this.selectMedicineSuggestion(bestMatch);
    }
    this.addPrescriptionMedicine();
  }

  addBestInvestigationFromKeyboard(): void {
    const bestMatch = this.filteredInvestigationSuggestions[0];
    if (bestMatch && this.investigationDraft.item_name.trim().length >= 2) {
      this.selectInvestigationSuggestion(bestMatch);
    }
    this.addInvestigation();
  }

  selectMedicineSuggestion(medicine: PharmacyMedicine | string, addNow = false): void {
    if (typeof medicine === 'string') {
      this.medicineDraft.item_name = medicine;
      if (addNow) this.addPrescriptionMedicine();
      return;
    }
    this.medicineDraft.item_name = medicine.name;
    this.medicineDraft.strength = medicine.strength || this.medicineDraft.strength;
    this.medicineSearch = '';
    if (addNow) this.addPrescriptionMedicine();
  }

  selectInvestigationSuggestion(item: PharmacyInvestigationSetting | string, addNow = false): void {
    if (typeof item === 'string') {
      this.investigationDraft.item_name = item;
      if (addNow) this.addInvestigation();
      return;
    }
    this.investigationDraft.item_name = item.test_name;
    this.investigationDraft.service_area = item.service_area || 'laboratory';
    this.investigationSearch = '';
    if (addNow) this.addInvestigation();
  }

  applyDiagnosis(value: string): void {
    this.prescriptionDraft.final_diagnosis = value;
    this.diagnosisSearch = '';
  }

  applyAdvice(value: string): void {
    const existing = this.prescriptionDraft.follow_up_note.trim();
    this.prescriptionDraft.follow_up_note = existing ? `${existing}\n${value}` : value;
    this.adviceSearch = '';
  }

  applyTemplate(template: PrescriptionTemplate): void {
    if (template.complaint) this.prescriptionDraft.chief_complaint = template.complaint;
    if (template.diagnosis) this.prescriptionDraft.final_diagnosis = template.diagnosis;
    template.advice.forEach((advice) => this.applyAdvice(advice));
    template.medicines.forEach((medicine) => {
      this.medicineDraft = { ...this.emptyMedicineDraft(), ...medicine, item_name: medicine.name };
      this.addPrescriptionMedicine(false);
    });
    template.investigations.forEach((investigation) => {
      this.investigationDraft = { ...this.emptyInvestigationDraft(), item_name: investigation.name, service_area: investigation.service_area };
      this.addInvestigation(false);
    });
  }

  saveConsultation(): void {
    if (!this.selectedVisit) return;
    this.savingConsultation = true;
    this.opdService
      .updateConsultation(this.selectedVisit.id, this.consultationPayload())
      .subscribe((visit) => {
        this.savingConsultation = false;
        this.setSelectedVisit(visit);
        this.applyVisitToPrescriptionDraft(visit);
        this.notificationService.success('Consultation saved.');
      }, () => (this.savingConsultation = false));
  }

  finalizePrescription(): void {
    if (!this.selectedVisit || !window.confirm('Finalize this prescription?')) return;
    this.savingConsultation = true;
    this.opdService.updateConsultation(this.selectedVisit.id, this.consultationPayload()).subscribe((visit) => {
      this.setSelectedVisit(visit);
      if (!this.session.hasPermission(PERMISSIONS.opdVisitManage)) {
        this.savingConsultation = false;
        this.notificationService.success('Prescription saved.');
        return;
      }
      this.opdService.updateStatus(visit.id, 'prescribed').subscribe((updatedVisit) => {
        this.savingConsultation = false;
        this.setSelectedVisit(updatedVisit);
        this.notificationService.success('Prescription finalized.');
      }, () => (this.savingConsultation = false));
    }, () => (this.savingConsultation = false));
  }

  addPrescriptionMedicine(showMessage = true): void {
    if (this.savingOrder) return;
    if (!this.selectedVisit || !this.medicineDraft.item_name.trim()) {
      this.notificationService.error('Enter a medicine before adding it to the prescription.');
      return;
    }
    this.savingOrder = true;
    this.opdService
      .createOrder(this.selectedVisit.id, {
        order_type: 'prescription',
        service_area: 'pharmacy',
        item_name: this.medicineTitle(this.medicineDraft),
        instructions: this.buildMedicineInstructions(this.medicineDraft) || null,
        quantity: Number(this.medicineDraft.quantity || 1),
      })
      .subscribe((visit) => {
        this.savingOrder = false;
        this.setSelectedVisit(visit);
        this.medicineDraft = this.emptyMedicineDraft();
        if (showMessage) this.notificationService.success('Medicine added.');
      }, () => (this.savingOrder = false));
  }

  addInvestigation(showMessage = true): void {
    if (this.savingOrder) return;
    if (!this.selectedVisit || !this.investigationDraft.item_name.trim()) {
      this.notificationService.error('Enter an investigation before adding it.');
      return;
    }
    this.savingOrder = true;
    this.opdService
      .createOrder(this.selectedVisit.id, {
        order_type: 'investigation',
        service_area: this.investigationDraft.service_area || 'laboratory',
        item_name: this.investigationDraft.item_name.trim(),
        instructions: this.investigationDraft.instructions.trim() || null,
        quantity: 1,
      })
      .subscribe((visit) => {
        this.savingOrder = false;
        this.setSelectedVisit(visit);
        this.investigationDraft = this.emptyInvestigationDraft();
        if (showMessage) this.notificationService.success('Investigation added.');
      }, () => (this.savingOrder = false));
  }

  editOrder(order: OPDVisitOrder): void {
    this.editingOrderId = order.id;
  }

  saveOrder(order: OPDVisitOrder): void {
    if (!this.selectedVisit) return;
    this.savingOrder = true;
    this.opdService
      .updateOrder(this.selectedVisit.id, order.id, {
        item_name: order.item_name,
        instructions: order.instructions || null,
        quantity: Number(order.quantity || 1),
        service_area: order.service_area || (order.order_type === 'prescription' ? 'pharmacy' : 'laboratory'),
        status: order.status,
      })
      .subscribe((visit) => {
        this.savingOrder = false;
        this.editingOrderId = '';
        this.setSelectedVisit(visit);
        this.notificationService.success('Prescription row updated.');
      }, () => (this.savingOrder = false));
  }

  removeOrder(order: OPDVisitOrder): void {
    if (!this.selectedVisit) return;
    if (!window.confirm(`Remove ${order.item_name} from this prescription?`)) return;
    this.savingOrder = true;
    this.opdService.deleteOrder(this.selectedVisit.id, order.id).subscribe((visit) => {
      this.savingOrder = false;
      this.setSelectedVisit(visit);
      this.notificationService.success('Prescription row removed.');
    }, () => (this.savingOrder = false));
  }

  copyPreviousOrder(order: OPDVisitOrder): void {
    if (!this.selectedVisit) return;
    this.opdService
      .createOrder(this.selectedVisit.id, {
        order_type: order.order_type,
        service_area: order.service_area || (order.order_type === 'prescription' ? 'pharmacy' : 'laboratory'),
        item_name: order.item_name,
        instructions: order.instructions || null,
        quantity: Number(order.quantity || 1),
      })
      .subscribe((visit) => this.setSelectedVisit(visit));
  }

  printPrescription(visit: OPDVisit): void {
    const layoutProfile = this.findProfile('prescription_layout', visit);
    const printed = printOPDPrescription({
      visit,
      doctor: this.doctorForVisit(visit),
      layoutProfile,
    });
    if (!printed) {
      this.notificationService.warning('Unable to open prescription print. Allow browser printing and try again.');
    }
  }

  private applyVisitToPrescriptionDraft(visit: OPDVisit): void {
    this.prescriptionDraft = {
      chief_complaint: visit.chief_complaint || '',
      history_of_present_illness: visit.history_of_present_illness || '',
      vital_signs: visit.vital_signs || '',
      examination_note: visit.examination_note || '',
      provisional_diagnosis: visit.provisional_diagnosis || '',
      final_diagnosis: visit.final_diagnosis || '',
      follow_up_date: visit.follow_up_date || '',
      follow_up_note: visit.follow_up_note || '',
      item_name: '',
      instructions: '',
      quantity: 1,
    };
  }

  private loadPrescriptionCatalog(): void {
    this.pharmacyService.listMedicines({ page_size: 30, is_active: true }).subscribe((response) => (this.pharmacyMedicines = response.items));
    this.pharmacyService.listInvestigationSettings({ page_size: 30, is_active: 'true' }).subscribe((response) => (this.investigationSettings = response.items));
  }

  private searchMedicineCatalog(query: string): void {
    const token = ++this.medicineSearchToken;
    this.medicineSuggestionsLoading = true;
    this.pharmacyService.listMedicines({ page_size: 12, q: query, is_active: true }).subscribe((response) => {
      if (token !== this.medicineSearchToken) return;
      this.medicineSuggestionsLoading = false;
      this.pharmacyMedicines = this.mergeMedicines(response.items, this.pharmacyMedicines);
    }, () => (this.medicineSuggestionsLoading = false));
  }

  private searchInvestigationCatalog(query: string): void {
    const token = ++this.investigationSearchToken;
    this.investigationSuggestionsLoading = true;
    this.pharmacyService.listInvestigationSettings({ page_size: 12, q: query, is_active: 'true' }).subscribe((response) => {
      if (token !== this.investigationSearchToken) return;
      this.investigationSuggestionsLoading = false;
      this.investigationSettings = this.mergeInvestigationSettings(response.items, this.investigationSettings);
    }, () => (this.investigationSuggestionsLoading = false));
  }

  private loadPreviousVisits(visit: OPDVisit): void {
    this.opdService.getPatientVisits(visit.patient.id).subscribe((visits) => {
      this.previousVisits = visits
        .filter((item) => item.id !== visit.id && item.orders.some((order) => ['prescription', 'investigation'].includes(order.order_type) && order.status !== 'cancelled'))
        .slice(0, 4);
    });
  }

  private setSelectedVisit(visit: OPDVisit): void {
    this.selectedVisit = {
      ...visit,
      orders: [...visit.orders].sort((a, b) => a.created_at.localeCompare(b.created_at)),
    };
    this.visits = this.visits.map((item) => (item.id === visit.id ? this.selectedVisit as OPDVisit : item));
  }

  private activeOrders(type: string): OPDVisitOrder[] {
    return (this.selectedVisit?.orders || []).filter((order) => order.order_type === type && order.status !== 'cancelled');
  }

  private emptyMedicineDraft(): MedicineDraft {
    return {
      item_name: '',
      strength: '',
      dosage: '1 tab',
      frequency: '1+0+1',
      duration: '5 days',
      route: 'Oral',
      timing: 'After meal',
      instructions: '',
      quantity: 1,
    };
  }

  private emptyInvestigationDraft(): InvestigationDraft {
    return { item_name: '', service_area: 'laboratory', instructions: '' };
  }

  private medicineTitle(draft: MedicineDraft): string {
    return [draft.item_name, draft.strength].filter(Boolean).join(' ').trim();
  }

  private buildMedicineInstructions(draft: MedicineDraft): string {
    return [draft.dosage, draft.frequency, draft.duration, draft.route, draft.timing, draft.instructions].filter(Boolean).join(' | ');
  }

  private consultationPayload() {
    return {
      chief_complaint: this.prescriptionDraft.chief_complaint || null,
      history_of_present_illness: this.prescriptionDraft.history_of_present_illness || null,
      vital_signs: this.prescriptionDraft.vital_signs || null,
      examination_note: this.prescriptionDraft.examination_note || null,
      provisional_diagnosis: this.prescriptionDraft.provisional_diagnosis || null,
      final_diagnosis: this.prescriptionDraft.final_diagnosis || null,
      follow_up_date: this.prescriptionDraft.follow_up_date || null,
      follow_up_note: this.prescriptionDraft.follow_up_note || null,
    };
  }

  private filterTextSuggestions(items: string[], query: string): string[] {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return items;
    return items.filter((item) => item.toLowerCase().includes(normalized));
  }

  private mergeMedicines(primary: PharmacyMedicine[], fallback: PharmacyMedicine[]): PharmacyMedicine[] {
    const merged = new Map<string, PharmacyMedicine>();
    [...primary, ...fallback].forEach((item) => merged.set(item.id, item));
    return Array.from(merged.values()).slice(0, 60);
  }

  private mergeInvestigationSettings(primary: PharmacyInvestigationSetting[], fallback: PharmacyInvestigationSetting[]): PharmacyInvestigationSetting[] {
    const merged = new Map<string, PharmacyInvestigationSetting>();
    [...primary, ...fallback].forEach((item) => merged.set(item.id, item));
    return Array.from(merged.values()).slice(0, 60);
  }

  private findProfile(type: string, visit: OPDVisit | null): ConfigurationProfile | null {
    if (!visit) return null;
    const doctorId = visit.consulting_doctor_user_id || visit.doctor_user_id;
    return (
      this.configurationProfiles.find((profile) => profile.profile_type === type && profile.target_id === doctorId) ||
      this.configurationProfiles.find((profile) => profile.profile_type === type && profile.is_default) ||
      null
    );
  }

  private doctorForVisit(visit: OPDVisit): User | null {
    const doctorId = visit.consulting_doctor_user_id || visit.doctor_user_id;
    return this.doctors.find((doctor) => doctor.id === doctorId) || null;
  }

  private profileList(profile: ConfigurationProfile | null, key: string): string[] {
    const value = profile?.payload?.[key];
    return Array.isArray(value) ? value.map(String).filter(Boolean) : [];
  }

  private normalizePrescriptionSections(payload: Record<string, unknown>): PrescriptionSectionView[] {
    const savedLabels = Array.isArray(payload['section_labels']) ? payload['section_labels'] as Array<Partial<PrescriptionSectionView> & { key?: string }> : [];
    const savedByKey = new Map(savedLabels.filter((item) => item.key).map((item) => [String(item.key), item]));
    const keys = Array.isArray(payload['sections']) ? payload['sections'].map(String) : DEFAULT_PRESCRIPTION_SECTIONS.map((section) => section.key);
    const structural = new Set(['header', 'patient', 'signature']);
    return keys
      .filter((key) => !structural.has(key))
      .map((key) => {
        const fallback = DEFAULT_PRESCRIPTION_SECTIONS.find((section) => section.key === key) || { key, label: this.sectionLabel(key), placement: 'full' as PrescriptionPlacement, height: 80 };
        const saved = savedByKey.get(key);
        return {
          key,
          label: String(saved?.label || fallback.label),
          placement: this.normalizePlacement(saved?.placement || fallback.placement),
          height: this.normalizeHeight(saved?.height || fallback.height),
        };
      });
  }

  private normalizePlacement(value: unknown): PrescriptionPlacement {
    return value === 'left' || value === 'right' || value === 'full' ? value : 'full';
  }

  private normalizeHeight(value: unknown): number {
    const height = Number(value || 80);
    return Number.isFinite(height) ? Math.min(Math.max(Math.round(height), 34), 320) : 80;
  }

  private normalizeColumnWidth(value: unknown): number {
    const width = Number(value || 38);
    return Number.isFinite(width) ? Math.min(Math.max(Math.round(width), 25), 65) : 38;
  }
}
