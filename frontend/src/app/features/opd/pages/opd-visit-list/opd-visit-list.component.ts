import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { PrescriptionField, PrescriptionFieldsComponent } from '../../../../shared/prescription-fields.component';
import { CommonModule } from '@angular/common';
import { Component, HostListener, OnDestroy, inject } from '@angular/core';
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
import { buildOPDPrescriptionHtml, printOPDPrescription } from '../../../../shared/utils/opd-prescription-printer';
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
  catalog_id?: string;
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
  imports: [CommonModule, FormsModule, PrescriptionFieldsComponent],
  templateUrl: './opd-visit-list.component.html',
  styleUrls: ['./opd-visit-list.component.scss'],
})
export class OPDVisitListComponent implements OnDestroy {
  private consultationSnapshot = '';
  private readonly opdService = inject(OPDService);
  private readonly pharmacyService = inject(PharmacyService);
  private readonly doctorDirectoryService = inject(DoctorDirectoryService);
  private readonly configurationService = inject(ConfigurationService);
  private readonly notificationService = inject(NotificationService);
  private readonly sanitizer = inject(DomSanitizer);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  readonly session = inject(SessionService);
  readonly permissions = PERMISSIONS;

  visits: OPDVisit[] = [];
  doctors: User[] = [];
  configurationProfiles: ConfigurationProfile[] = [];
  selectedDoctorUserId = '';
  searchText = '';
  selectedVisitType = '';
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
  private lastMedicineQuery = '';
  private medicineQueryCache = new Map<string,{at:number;items:PharmacyMedicine[]}>();
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

  extraClinicalData: Record<string,any> = {};
  templateId = '';
  autosaveMessage = '';
  prescribingHistory: {item_name:string;order_type:string;uses:number}[] = [];
  shortcuts: {id:string;name:string;kind:string;content:Record<string,any>}[] = [];
  private draftTimer = setInterval(()=>this.autosave(),2000);
  private templateLoadToken = 0;
  private visitLoadToken = 0;
  private autosaveBlocked = false;
  private autosaveFailures = 0;
  private nextAutosaveAt = 0;

  constructor() {
    this.doctorDirectoryService.listDoctors().subscribe((doctors) => (this.doctors = doctors));
    if(this.session.hasPermission('settings.configuration.manage')) this.configurationService.workspace().subscribe((workspace) => (this.configurationProfiles = workspace.profiles));
    this.loadPrescriptionCatalog();
    this.loadVisits();
    this.route.queryParamMap.subscribe((params) => {
      // Dashboard cards open this list already filtered (status, payment, day).
      this.selectedStatus = params.get('status') ?? this.selectedStatus;
      this.selectedVisitType = params.get('visitType') ?? this.selectedVisitType;
      this.selectedPayment = params.get('payment') ?? this.selectedPayment;
      this.selectedDate = params.get('date') ?? this.selectedDate;
      const openVisit = params.get('openVisit');
      if (openVisit) {
        this.openVisit(openVisit);
      }
    });
  }

  accessNotice = "";
  loadVisits(): void {
    this.accessNotice="";
    const doctorUserId = this.selectedDoctorUserId || null;
    this.opdService.listVisits(doctorUserId).subscribe({next:visits=>this.visits=visits,error:error=>{this.visits=[];this.accessNotice=error.status===403 ? "Doctor access has not been assigned to your account. Ask administration to grant access to the doctors you support; registration and appointment check-in remain available." : "Visits could not be loaded. Check your connection and refresh.";}});
  }

  openVisit(visitId: string): void {
    if (this.hasUnsavedChanges() && !window.confirm('Discard the unsaved prescription changes and open this visit?')) return;
    const discardKey=this.hasUnsavedChanges()?this.draftKey():null;
    const loadToken=++this.visitLoadToken;
    this.opdService.getVisit(visitId).subscribe((visit) => {
      if(loadToken!==this.visitLoadToken)return;
      if(discardKey)sessionStorage.removeItem(discardKey);
      this.setSelectedVisit(visit, true);
      this.applyVisitToPrescriptionDraft(visit,true);
      this.loadPreviousVisits(visit);
      this.loadClinicalTools(visit);
    });
  }

  closeVisit(): void {
    if (this.hasUnsavedChanges() && !window.confirm('Discard the unsaved prescription changes?')) return;
    sessionStorage.removeItem(this.draftKey());
    this.visitLoadToken++;this.templateLoadToken++;
    this.selectedVisit = null;
  }

  hasUnsavedChanges(): boolean {
    return !!this.selectedVisit && ((!!this.consultationSnapshot && this.draftFingerprint() !== this.consultationSnapshot) || !!this.medicineDraft.item_name.trim() || !!this.investigationDraft.item_name.trim() || !!this.editingOrderId);
  }

  @HostListener('window:beforeunload', ['$event'])
  protectDraft(event: BeforeUnloadEvent): void {
    if (this.hasUnsavedChanges()) { event.preventDefault(); event.returnValue = ''; }
  }

  ngOnDestroy(): void {
    this.closePrescriptionPreview();
    clearInterval(this.draftTimer);
    if (this.medicineSearchTimer) clearTimeout(this.medicineSearchTimer);
    if (this.investigationSearchTimer) clearTimeout(this.investigationSearchTimer);
  }

  navigateToQueue(): void {
    void this.router.navigate(['/opd/queue']);
  }

  navigateToRegisterVisit(): void {
    void this.router.navigate(['/opd/register']);
  }

  navigateToNewPatient(): void {
    void this.router.navigate(['/patients/new'], { queryParams: { returnTo: '/opd/register' } });
  }

  startVisit(visit: OPDVisit): void {
    if (!this.canStartVisit) return;
    if (this.savingConsultation) return;
    const sameOpenVisit=this.selectedVisit?.id===visit.id;
    if (!sameOpenVisit && this.hasUnsavedChanges() && !window.confirm('Discard your unsaved consultation changes before starting this visit?')) return;
    if (visit.status === 'in_consultation') {
      this.openVisit(visit.id);
      return;
    }
    this.savingConsultation = true;
    const loadToken=++this.visitLoadToken;
    this.opdService.updateStatus(visit.id, 'in_consultation').subscribe({
      next: updated => {
        this.savingConsultation = false;
        if(loadToken!==this.visitLoadToken)return;
        this.setSelectedVisit(updated,true);
        if(!sameOpenVisit)this.applyVisitToPrescriptionDraft(updated,true);
        this.loadPreviousVisits(updated);
        if(!sameOpenVisit)this.loadClinicalTools(updated);
      },
      error: error => {
        this.savingConsultation = false;
        this.notificationService.error(error?.message || 'Unable to start this consultation. Check the doctor’s current patient.');
      },
    });
  }

  openPayment(visit: OPDVisit): void {
    if (!this.session.hasPermission(PERMISSIONS.billingPaymentCollect)) return;
    void this.router.navigate(['/billing/create'], { queryParams: { opdVisitId: visit.id } });
  }

  convertToIpd(visit: OPDVisit): void {
    if (!this.session.hasAnyPermission([PERMISSIONS.ipdAdmit, PERMISSIONS.ipdAdmissionManage])) return;
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
      const paymentMatch = !this.selectedPayment || (this.selectedPayment === 'due' ? ['unpaid', 'partial'].includes(paymentStatus) : paymentStatus === this.selectedPayment);
      const dateMatch = !this.selectedDate || visit.visit_date === this.selectedDate;
      const searchMatch =
        !search ||
        visit.visit_number.toLowerCase().includes(search) ||
        `${visit.patient.first_name} ${visit.patient.last_name}`.toLowerCase().includes(search) ||
        visit.patient.patient_number.toLowerCase().includes(search) ||
        (visit.consulting_doctor_name || '').toLowerCase().includes(search) ||
        (visit.department_name || '').toLowerCase().includes(search);
      return statusMatch && paymentMatch && dateMatch && searchMatch && (!this.selectedVisitType || visit.visit_type===this.selectedVisitType);
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
    return this.session.hasPermission(PERMISSIONS.opdVisitManage);
  }

  get activeLayoutProfile(): ConfigurationProfile | null {
    const frozen=this.selectedVisit?.signed_prescription;
    if(this.isSigned && frozen?.['template_payload'])return {id:frozen['template_id'] || '',name:'Signed template v'+(frozen['template_version'] || 'legacy'),payload:frozen['template_payload'],profile_type:'prescription_layout'} as ConfigurationProfile;
    return this.configurationProfiles.find(p=>p.id===this.templateId) || this.findProfile('prescription_layout', this.selectedVisit);
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
    return this.shortcuts.filter(s=>s.kind==='combination').map(s=>({name:s.name,complaint:'',diagnosis:'',medicines:[],investigations:[],advice:[],...s.content}));
  }

  get filteredMedicineSuggestions(): PharmacyMedicine[] {
    const query = (this.medicineSearch || this.medicineDraft.item_name).trim().toLowerCase();
    const favorites = new Set(this.medicineSuggestions.map((item) => item.toLowerCase()));
    const pool = [...this.pharmacyMedicines].sort((a, b) => {
      const favoriteSort = (favorites.has(a.name.toLowerCase()) ? 0 : 1) - (favorites.has(b.name.toLowerCase()) ? 0 : 1);
      return favoriteSort || a.name.localeCompare(b.name);
    });
    if (!query || (this.medicineSearch.trim() && this.lastMedicineQuery.toLowerCase()===query)) return pool.slice(0, 8);
    return pool.filter((medicine) => [medicine.name, medicine.generic_name, medicine.strength, medicine.dosage_form, medicine.description].filter(Boolean).join(' ').toLowerCase().includes(query)).slice(0, 8);
  }

  get filteredInvestigationSuggestions(): PharmacyInvestigationSetting[] {
    const query = (this.investigationSearch || this.investigationDraft.item_name).trim().toLowerCase();
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
    this.medicineDraft.catalog_id = undefined;
    this.medicineSearch = query;
    if (this.medicineSearchTimer) window.clearTimeout(this.medicineSearchTimer);
    const normalized = query.trim();
    if (normalized.length < 1) return;
    this.medicineSearchTimer = window.setTimeout(() => this.searchMedicineCatalog(normalized), 160);
  }

  onInvestigationQueryChanged(query: string): void {
    this.investigationSearch = query;
    if (this.investigationSearchTimer) window.clearTimeout(this.investigationSearchTimer);
    const normalized = query.trim();
    if (normalized.length < 1) return;
    this.investigationSearchTimer = window.setTimeout(() => this.searchInvestigationCatalog(normalized), 160);
  }

  addBestMedicineFromKeyboard(): void {
    if (!this.medicineDraft.catalog_id) { this.notificationService.warning('Select the intended medicine from the catalog, then enter its instructions.'); return; }
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
    this.medicineDraft.catalog_id = medicine.id;
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
    if(!this.selectedVisit || this.savingOrder || this.isSigned)return;
    if(template.complaint)this.prescriptionDraft.chief_complaint=template.complaint;
    if(template.diagnosis)this.prescriptionDraft.final_diagnosis=template.diagnosis;
    template.advice.forEach(advice=>this.applyAdvice(advice));
    const orders=[...template.medicines.map(m=>({order_type:'prescription',item_name:[m.name,m.strength].filter(Boolean).join(' '),instructions:this.buildMedicineInstructions({...this.emptyMedicineDraft(),...m,item_name:m.name}),quantity:m.quantity||1,request_key:crypto.randomUUID(),prescription_detail:{...m,confirmed_by_doctor:true}})),...template.investigations.map(i=>({order_type:'investigation',service_area:i.service_area,item_name:i.name,quantity:1,request_key:crypto.randomUUID()}))];
    if(!orders.length)return;this.savingOrder=true;
    this.opdService.clinicalPost<OPDVisit>('visits/'+this.selectedVisit.id+'/orders-batch',orders).subscribe({next:visit=>{this.savingOrder=false;this.setSelectedVisit(visit);},error:()=>this.savingOrder=false});
  }
  saveCombination():void {
    if(!this.selectedVisit)return;const name=window.prompt('Name for this medicine / investigation combination');if(!name?.trim())return;
    this.saveShortcut('combination',name,{medicines:this.activePrescriptionOrders.map(order=>({...(order.prescription_detail||{}),name:order.prescription_detail?.['catalog_snapshot']?.name || order.item_name,instructions:order.instructions,quantity:order.quantity})),investigations:this.activeInvestigationOrders.map(order=>({name:order.item_name,service_area:order.service_area})),advice:[]});
  }

  saveConsultation(): void {
    if (!this.selectedVisit || this.isSigned || !this.canPrescribe || this.savingConsultation) return;
    const identity=this.selectedVisit.id;const fingerprint=this.draftFingerprint();
    this.savingConsultation=true;
    this.opdService.updateConsultation(identity,this.consultationPayload()).subscribe({next:visit=>{
      this.savingConsultation=false;if(this.selectedVisit?.id!==identity)return;
      const unchanged=this.draftFingerprint()===fingerprint;
      this.setSelectedVisit(visit);
      if(unchanged)this.applyVisitToPrescriptionDraft(visit);else this.consultationSnapshot=fingerprint;
      this.notificationService.success('Consultation saved.');
    },error:()=>this.savingConsultation=false});
  }

  finalizePrescription(): void {
    if (!this.selectedVisit || this.savingConsultation || this.savingOrder) return;
    if(this.medicineDraft.item_name.trim() || this.investigationDraft.item_name.trim() || this.editingOrderId){this.notificationService.warning('Add or discard unfinished medicine/investigation entries before signing');return;}
    if (this.selectedVisit.status !== 'in_consultation' && this.selectedVisit.prescription_status !== 'amended') {
      this.notificationService.warning('Start this consultation before finalizing its prescription.');
      return;
    }
    if (!window.confirm('Finalize this prescription and release the doctor’s current serial?')) return;
    this.savingConsultation = true;
    this.opdService.finalizePrescription(this.selectedVisit.id, this.consultationPayload()).subscribe({
      next: visit => {
        this.savingConsultation = false;
        if(!this.setSelectedVisit(visit))return;
        this.applyVisitToPrescriptionDraft(visit);
        this.notificationService.success('Prescription finalized.', 'Print the prescription, review billing, or send the patient to IPD if needed.');
      },
      error: error => {
        this.savingConsultation = false;
        this.notificationService.error(error?.message || 'Finalization failed. Your draft is still open; review it and try again.');
      },
    });
  }

  addPrescriptionMedicine(showMessage = true): void {
    if (this.savingOrder) return;
    if (!this.selectedVisit || !this.medicineDraft.item_name.trim()) {
      this.notificationService.error('Enter a medicine before adding it to the prescription.');
      return;
    }
    if (!this.medicineDraft.dosage.trim() || !this.medicineDraft.frequency.trim()) {this.notificationService.warning('Enter and confirm the dose and frequency; no dose is inferred.');return;}
    this.savingOrder = true;
    this.opdService
      .createOrder(this.selectedVisit.id, {
        request_key: crypto.randomUUID(),
        prescription_detail: {...this.medicineDraft, confirmed_by_doctor: true},
        order_type: 'prescription',
        service_area: 'pharmacy',
        item_name: this.medicineTitle(this.medicineDraft),
        instructions: this.buildMedicineInstructions(this.medicineDraft) || null,
        quantity: Number(this.medicineDraft.quantity || 1),
      })
      .subscribe((visit) => {
        this.savingOrder = false;
        if(!this.setSelectedVisit(visit))return;
        this.medicineDraft = this.emptyMedicineDraft();
        this.persistLocalDraft();
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
        if(!this.setSelectedVisit(visit))return;
        this.investigationDraft = this.emptyInvestigationDraft();
        this.persistLocalDraft();
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
        expected_version: order.version,
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

  prescriptionVersions: Array<{version:number;status:string;signed_at:string|null;reason:string|null;snapshot:Record<string,any>}> = [];
  prescriptionAudit: Array<{kind:string;created_at:string;detail:Record<string,any>}> = [];
  loadPrescriptionHistory():void {
    if(!this.selectedVisit)return;const identity=this.selectedVisit.id;
    this.opdService.clinicalGet<typeof this.prescriptionVersions>('visits/'+identity+'/prescription-history').subscribe(rows=>{if(this.selectedVisit?.id===identity)this.prescriptionVersions=rows;});
    this.opdService.clinicalGet<typeof this.prescriptionAudit>('visits/'+identity+'/prescription-audit').subscribe(rows=>{if(this.selectedVisit?.id===identity)this.prescriptionAudit=rows;});
  }
  previewPrescriptionVersion(row:typeof this.prescriptionVersions[number]):void {
    if(!this.selectedVisit)return;
    this.printPrescription({...this.selectedVisit,prescription_status:row.status==='voided'?'voided':'finalized',signed_prescription:{...row.snapshot,_historical_version:row.version}});
  }

  prescriptionPreviewUrl: SafeResourceUrl | null = null;
  private previewBlobUrl: string | null = null;
  printPrescription(visit: OPDVisit): void {
    if(!this.canPrescribe && visit.prescription_status!=='finalized'){this.notificationService.warning('Only finalized prescriptions can be printed by non-prescribers');return;}
    const isCurrentDraft=visit.id===this.selectedVisit?.id && !visit.signed_prescription?.['_historical_version'] && !['finalized','voided'].includes(visit.prescription_status || 'draft');
    if(isCurrentDraft)visit={...visit,...this.prescriptionDraft,prescription_data:{...this.extraClinicalData},prescription_template_id:this.templateId || null};
    const layoutProfile=isCurrentDraft?this.activeLayoutProfile:this.findProfile('prescription_layout',visit);
    const html=buildOPDPrescriptionHtml({visit,doctor:this.doctorForVisit(visit),layoutProfile});
    if(this.previewBlobUrl)URL.revokeObjectURL(this.previewBlobUrl);
    this.previewBlobUrl=URL.createObjectURL(new Blob([html],{type:'text/html;charset=utf-8'}));
    this.prescriptionPreviewUrl=this.sanitizer.bypassSecurityTrustResourceUrl(this.previewBlobUrl);
  }
  printPrescriptionPreview():void {const frame=document.querySelector<HTMLIFrameElement>('.prescription-preview-frame');frame?.contentWindow?.focus();frame?.contentWindow?.print();}
  closePrescriptionPreview():void {this.prescriptionPreviewUrl=null;if(this.previewBlobUrl)URL.revokeObjectURL(this.previewBlobUrl);this.previewBlobUrl=null;}

  private applyVisitToPrescriptionDraft(visit: OPDVisit, resetEntries = false): void {
    if(resetEntries){this.prescriptionVersions=[];this.prescriptionAudit=[];this.medicineDraft=this.emptyMedicineDraft();this.investigationDraft=this.emptyInvestigationDraft();this.editingOrderId='';}
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
    this.extraClinicalData = {...(visit.prescription_data || {})};
    this.templateId = visit.prescription_template_id || '';
    this.autosaveBlocked=false;this.autosaveFailures=0;this.nextAutosaveAt=0;
    this.consultationSnapshot = this.draftFingerprint();
  }

  private loadPrescriptionCatalog(): void {
    if(!this.session.hasPermission('opd.prescribe')) return;
    this.pharmacyService.prescribingMedicines({ page_size: 30, is_active: true }).subscribe((response) => (this.pharmacyMedicines = response.items));
    (this.pharmacyService.prescribingInvestigations ? this.pharmacyService.prescribingInvestigations({page_size:30}) : this.pharmacyService.listInvestigationSettings({ page_size: 30, is_active: 'true' })).subscribe((response) => (this.investigationSettings = response.items));
  }

  private searchMedicineCatalog(query: string): void {
    const cached=this.medicineQueryCache.get(query.toLowerCase());
    if(cached && Date.now()-cached.at<60000){this.lastMedicineQuery=query;this.pharmacyMedicines=cached.items;return;}
    const token = ++this.medicineSearchToken;
    this.medicineSuggestionsLoading = true;
    this.pharmacyService.prescribingMedicines({ page_size: 12, q: query, is_active: true }).subscribe((response) => {
      if (token !== this.medicineSearchToken) return;
      this.medicineSuggestionsLoading = false;
      this.lastMedicineQuery = query;
      if(this.medicineQueryCache.size>=30)this.medicineQueryCache.delete(this.medicineQueryCache.keys().next().value!);
      this.medicineQueryCache.set(query.toLowerCase(),{at:Date.now(),items:response.items});
      this.pharmacyMedicines = response.items;
    }, () => (this.medicineSuggestionsLoading = false));
  }

  private searchInvestigationCatalog(query: string): void {
    const token = ++this.investigationSearchToken;
    this.investigationSuggestionsLoading = true;
    (this.pharmacyService.prescribingInvestigations ? this.pharmacyService.prescribingInvestigations({page_size:12,q:query}) : this.pharmacyService.listInvestigationSettings({ page_size: 12, q: query, is_active: 'true' })).subscribe((response) => {
      if (token !== this.investigationSearchToken) return;
      this.investigationSuggestionsLoading = false;
      this.investigationSettings = this.mergeInvestigationSettings(response.items, this.investigationSettings);
    }, () => (this.investigationSuggestionsLoading = false));
  }

  private loadPreviousVisits(visit: OPDVisit): void {
    this.opdService.getPatientVisits(visit.patient.id).subscribe((visits) => {
      if(this.selectedVisit?.id!==visit.id)return;
      this.previousVisits = visits
        .filter((item) => item.id !== visit.id && item.orders.some((order) => ['prescription', 'investigation'].includes(order.order_type) && order.status !== 'cancelled'))
        .slice(0, 4);
    });
  }

  private setSelectedVisit(visit: OPDVisit, allowSwitch = false): boolean {
    if(!allowSwitch && (!this.selectedVisit || this.selectedVisit.id!==visit.id)){this.visits=this.visits.map(item=>item.id===visit.id?visit:item);return false;}
    this.selectedVisit = {
      ...visit,
      orders: [...visit.orders].sort((a, b) => a.created_at.localeCompare(b.created_at)),
    };
    this.visits = this.visits.map((item) => (item.id === visit.id ? this.selectedVisit as OPDVisit : item));
    return true;
  }

  private activeOrders(type: string): OPDVisitOrder[] {
    return (this.selectedVisit?.orders || []).filter((order) => order.order_type === type && order.status !== 'cancelled' && !order.prescription_detail?.['_withdrawn_from_rx']);
  }

  private emptyMedicineDraft(): MedicineDraft {
    return {
      item_name: '',
      strength: '',
      dosage: '',
      frequency: '',
      duration: '',
      route: '',
      timing: '',
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
      expected_version: this.selectedVisit?.clinical_version,
      prescription_data: this.extraClinicalData,
      prescription_template_id: this.templateId || null,
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

  get previousAllergies():string {return String(this.previousVisits.find(visit=>visit.prescription_data?.['allergies'])?.prescription_data?.['allergies'] || '');}
  get ingredientWarnings():string[] {const groups=new Map<string,number>();for(const order of this.activePrescriptionOrders){const generic=order.prescription_detail?.['catalog_snapshot']?.generic;if(generic)groups.set(generic,(groups.get(generic)||0)+1);}return [...groups].filter(([,count])=>count>1).map(([generic])=>'Review duplicate catalog ingredient: '+generic+'. No automatic substitution or dose adjustment was made.');}
  get frequencyInterpretation():string {const match=this.medicineDraft.frequency.match(/^(\d+(?:\.\d+)?)\+(\d+(?:\.\d+)?)\+(\d+(?:\.\d+)?)$/);return match?'Recorded shorthand: morning '+match[1]+', midday '+match[2]+', evening '+match[3]+'. Confirm the intended dose and timing.':'';}

  searchCustomCatalog(event:{kind:string;query:string}):void {if(event.kind==='medicine'){if(this.medicineSearchTimer)clearTimeout(this.medicineSearchTimer);this.medicineSearchTimer=setTimeout(()=>this.searchMedicineCatalog(event.query),160);}else{if(this.investigationSearchTimer)clearTimeout(this.investigationSearchTimer);this.investigationSearchTimer=setTimeout(()=>this.searchInvestigationCatalog(event.query),160);}}
  selectCustomCatalog(event:{kind:string;item:any}):void {if(event.kind==='medicine'){this.selectMedicineSuggestion(event.item,false);this.focusClinicalSection('medicine');}else this.selectInvestigationSuggestion(event.item,true);}
  focusClinicalSection(kind:string):void {const placeholder=kind==='medicine'?'Medicine name':'Search lab or radiology test';const input=document.querySelector<HTMLInputElement>('input[placeholder="'+placeholder+'"]');input?.scrollIntoView({block:'center',behavior:'smooth'});input?.focus();}

  get templateFields(): PrescriptionField[] {return (this.activeLayoutProfile?.payload['fields'] as PrescriptionField[]) || [];}
  get canPrescribe():boolean {return this.session.hasPermission('opd.prescribe');}
  get isSigned(): boolean {return ['finalized','voided'].includes(this.selectedVisit?.prescription_status || '');}
  private draftFingerprint():string {const {expected_version,...content}=this.consultationPayload();return JSON.stringify(content);}
  private draftKey():string {return 'hms.rx.draft:'+this.session.snapshot.user?.id+':'+this.selectedVisit?.id;}
  private loadClinicalTools(visit:OPDVisit):void {
    if(!this.session.hasPermission('opd.prescribe') || !this.opdService.clinicalGet)return;
    const token=++this.templateLoadToken;
    this.opdService.clinicalGet<ConfigurationProfile[]>('visits/'+visit.id+'/prescription-templates').subscribe(rows=>{
      if(token!==this.templateLoadToken || this.selectedVisit?.id!==visit.id || this.isSigned)return;
      this.configurationProfiles=[...this.configurationProfiles.filter(p=>p.profile_type!=='prescription_layout'),...rows];
      this.templateId=visit.prescription_template_id || rows[0]?.id || '';
      this.applyFieldDefaults();
      try {const raw=sessionStorage.getItem(this.draftKey());if(raw&&!this.isSigned){const saved=JSON.parse(raw);if(saved.version===(visit.clinical_version||0)){this.prescriptionDraft={...this.prescriptionDraft,...saved.draft};this.extraClinicalData=saved.extra;this.medicineDraft={...this.emptyMedicineDraft(),...(saved.medicine||{})};this.investigationDraft={...this.emptyInvestigationDraft(),...(saved.investigation||{})};this.templateId=saved.templateId||this.templateId;this.autosaveMessage='Recovered interrupted draft';}else{this.autosaveMessage='A local draft exists from an older version. Reload history before copying changes.';}}}catch{}
    });
    this.opdService.clinicalGet<typeof this.shortcuts>('prescription-shortcuts').subscribe(rows=>this.shortcuts=rows);
    this.opdService.clinicalGet<{frequent:Array<{item_name:string;order_type:string;uses:number}>}>('prescribing-history').subscribe(response=>this.prescribingHistory=response.frequent);
  }
  applyFieldDefaults():void {for(const field of this.templateFields){if(field.key==='date_of_birth' && this.extraClinicalData[field.key]===undefined && this.selectedVisit?.patient.date_of_birth)this.extraClinicalData[field.key]=this.selectedVisit.patient.date_of_birth;if(this.extraClinicalData[field.key]===undefined&&field.default!=null)this.extraClinicalData[field.key]=field.default;}}
  @HostListener('input')
  @HostListener('change')
  checkpointDraft():void {queueMicrotask(()=>this.persistLocalDraft());}
  persistLocalDraft():void {
    if(!this.selectedVisit || !this.canPrescribe || this.isSigned)return;
    try {if(!this.hasUnsavedChanges()){sessionStorage.removeItem(this.draftKey());return;}sessionStorage.setItem(this.draftKey(),JSON.stringify({version:this.selectedVisit.clinical_version||0,draft:this.prescriptionDraft,extra:this.extraClinicalData,medicine:this.medicineDraft,investigation:this.investigationDraft,templateId:this.templateId}));}catch{this.autosaveMessage='Local storage unavailable; keep this window open until saved';}
  }
  autosave():void {
    if(!this.selectedVisit || this.autosaveBlocked || Date.now()<this.nextAutosaveAt || !this.canPrescribe || this.isSigned || this.savingConsultation || this.savingOrder || this.draftFingerprint()===this.consultationSnapshot)return;
    const visitId=this.selectedVisit.id;const fingerprint=this.draftFingerprint();
    this.persistLocalDraft();
    this.savingConsultation=true;this.autosaveMessage='Saving draft…';
    this.opdService.updateConsultation(visitId,this.consultationPayload(),true).subscribe({next:visit=>{
      this.savingConsultation=false;if(this.selectedVisit?.id!==visitId)return;
      this.selectedVisit={...this.selectedVisit,clinical_version:visit.clinical_version,prescription_data:visit.prescription_data,prescription_template_id:visit.prescription_template_id};
      this.consultationSnapshot=fingerprint;this.autosaveFailures=0;this.nextAutosaveAt=0;this.autosaveMessage='Draft saved';
      this.persistLocalDraft();
    },error:error=>{this.savingConsultation=false;this.autosaveBlocked=error.status===409;this.nextAutosaveAt=Date.now()+Math.min(30000,2000*2**(++this.autosaveFailures));this.autosaveMessage=error.status===409?'Draft conflict: another session saved changes. Reload before saving.':'Offline: draft retained in this browser session';}});
  }
  @HostListener('document:keydown',['$event'])
  prescriptionShortcut(event:KeyboardEvent):void {if(!this.selectedVisit)return;if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='s'){event.preventDefault();this.saveConsultation();}if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='p'){event.preventDefault();this.printPrescription(this.selectedVisit);}}
  amendPrescription(voided=false):void {
    if(!this.selectedVisit)return;const reason=window.prompt(voided?'Reason for marking prescription entered in error':'Reason for prescription amendment');if(!reason||reason.trim().length<3)return;
    this.opdService.clinicalPost<OPDVisit>('visits/'+this.selectedVisit.id+(voided?'/prescription-void':'/prescription-amend'),{reason,expected_version:this.selectedVisit.clinical_version||0}).subscribe(visit=>{if(this.setSelectedVisit(visit))this.applyVisitToPrescriptionDraft(visit);});
  }
  externalPaymentClaims:any[]=[];
  externalPaymentReviews:any[]=[];
  loadExternalPayments():void {
    if(!this.selectedVisit)return;const identity=this.selectedVisit.id;
    this.opdService.clinicalGet<any[]>('visits/'+identity+'/external-payments').subscribe(rows=>{if(this.selectedVisit?.id===identity)this.externalPaymentClaims=rows;});
    this.opdService.clinicalGet<any[]>('visits/'+identity+'/prescription-audit').subscribe(rows=>{if(this.selectedVisit?.id===identity)this.externalPaymentReviews=rows.filter(row=>row.kind==='external_payment_review');});
  }
  externalReview(claim:any):any {return this.externalPaymentReviews.find(row=>row.detail?.claim_id===claim.id)?.detail;}
  linkExternalRemittance(claim:any):void {
    if(!this.selectedVisit)return;
    const journal_id=window.prompt('Posted accounting receipt UUID. Source module: opd_external_remittance. Source reference: '+claim.id);if(!journal_id)return;
    const amount=window.prompt('Amount of hospital share received (BDT)',claim.hospital_share_remaining);if(!amount)return;
    const evidence=window.prompt('Finance remittance evidence / receipt reference');if(!evidence || evidence.trim().length<3)return;
    this.opdService.clinicalPost<any>('visits/'+this.selectedVisit.id+'/external-payments/'+claim.id+'/remittances',{journal_id,amount,evidence,request_key:crypto.randomUUID()}).subscribe(()=>{this.loadExternalPayments();this.notificationService.success('Existing cash receipt linked; no duplicate collection created');});
  }
  reviewExternalPayment(claim:any,decision:string):void {
    if(!this.selectedVisit)return;const evidence=window.prompt('Finance evidence / reconciliation reference. Verification records no hospital cash; actual remittance must be posted separately.');if(!evidence || evidence.trim().length<3)return;
    this.opdService.clinicalPost<any>('visits/'+this.selectedVisit.id+'/external-payments/'+claim.id+'/review',{decision,evidence,request_key:crypto.randomUUID()}).subscribe(()=>{this.loadExternalPayments();this.notificationService.success('Finance review saved; hospital cash unchanged');});
  }
  recordDirectPayment(kind='doctor_direct'):void {
    if(!this.selectedVisit)return;const reason=window.prompt('Payment information / waiver reason');if(!reason||reason.trim().length<3)return;
    const amount=kind==='doctor_direct'?window.prompt('Amount received directly by doctor (BDT)'): '0';if(amount===null)return;
    this.opdService.clinicalPost<OPDVisit>('visits/'+this.selectedVisit.id+'/external-payment',{kind,amount,reason,request_key:crypto.randomUUID()}).subscribe(visit=>{this.setSelectedVisit(visit);this.notificationService.success('Payment information recorded separately from hospital cash');});
  }
  saveShortcut(kind:string,name:string,content:Record<string,unknown>):void {this.opdService.clinicalPost<any>('prescription-shortcuts',{kind,name,content}).subscribe(row=>this.shortcuts=[...this.shortcuts,row]);}
  usePreviousName(item:typeof this.prescribingHistory[number]):void {if(item.order_type==='prescription'){this.medicineDraft=this.emptyMedicineDraft();this.medicineDraft.item_name=item.item_name;this.onMedicineQueryChanged(item.item_name);}else{this.investigationDraft={...this.emptyInvestigationDraft(),item_name:item.item_name};this.onInvestigationQueryChanged(item.item_name);}}
  favoriteMedicine():void {if(this.medicineDraft.item_name)this.saveShortcut('medicine',this.medicineDraft.item_name,{...this.medicineDraft});}
  favoriteInvestigation():void {if(this.investigationDraft.item_name)this.saveShortcut('investigation',this.investigationDraft.item_name,{...this.investigationDraft});}
  saveAdviceSnippet():void {const text=this.prescriptionDraft.follow_up_note.trim();if(text)this.saveShortcut('advice',text.slice(0,100),{text});}
  insertShortcut(shortcut:typeof this.shortcuts[number]):void {if(shortcut.kind==='medicine')this.medicineDraft={...this.emptyMedicineDraft(),...shortcut.content};else if(shortcut.kind==='investigation')this.investigationDraft={...this.emptyInvestigationDraft(),...shortcut.content};else this.prescriptionDraft.follow_up_note=[this.prescriptionDraft.follow_up_note,shortcut.content['text']||''].filter(Boolean).join('\n');}

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
    const sectionKeys=payload['editor_sections'] ?? payload['sections'];
    const keys = Array.isArray(sectionKeys) ? sectionKeys.map(String) : DEFAULT_PRESCRIPTION_SECTIONS.map((section) => section.key);
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
