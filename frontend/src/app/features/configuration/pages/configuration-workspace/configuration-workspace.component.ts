import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';

import { User } from '../../../../core/models/auth.models';
import { ActionConfirmationService } from '../../../../core/services/action-confirmation.service';
import { DoctorDirectoryService } from '../../../../core/services/doctor-directory.service';
import { NotificationService } from '../../../../core/services/notification.service';
import { ConfigurationProfile, ConfigurationService, ConfigurationWorkspace } from '../../services/configuration.service';

type ConfigType = 'doctor_share' | 'prescription_suggestion' | 'prescription_layout' | 'invoice_layout' | 'patient_portal_settings' | 'patient_bot_settings';
type ConfigContext = 'admin' | 'opd';
type ShareMethod = 'percentage' | 'fixed';
type SectionPlacement = 'full' | 'left' | 'right';

interface BuilderDraft {
  code: string;
  name: string;
  description: string;
  scope: string;
  target_type: string;
  target_id: string;
  is_default: boolean;
}

interface DoctorShareDraft extends BuilderDraft {
  method: ShareMethod;
  consultation_fee: number;
  doctor_share_percentage: number;
  doctor_share_amount: number;
  follow_up_share_percentage: number;
  hospital_share_percentage: number;
  applies_to_follow_up: boolean;
  notes: string;
}

interface SuggestionDraft extends BuilderDraft {
  complaints: string[];
  diagnoses: string[];
  medicines: string[];
  investigations: string[];
  advice: string[];
  follow_up_days: number;
}

interface PrescriptionSection {
  key: string;
  label: string;
  enabled: boolean;
  placement: SectionPlacement;
  height: number;
}

interface LayoutDraft extends BuilderDraft {
  paper_size: string;
  layout: string;
  font_size: number;
  left_column_width: number;
  show_logo: boolean;
  show_barcode: boolean;
  show_qr: boolean;
  footer_note: string;
  sections: PrescriptionSection[];
}

interface GenericDraft extends BuilderDraft {
  enabled: boolean;
  allow_appointment_booking: boolean;
  allow_online_payment: boolean;
  allow_family_access: boolean;
  allow_document_download: boolean;
  show_billing_details: boolean;
  footer_note: string;
}

const SECTION_LIBRARY: PrescriptionSection[] = [
  { key: 'header', label: 'Doctor Header', enabled: true, placement: 'full', height: 64 },
  { key: 'patient', label: 'Patient Details', enabled: true, placement: 'full', height: 40 },
  { key: 'vitals', label: 'Vitals', enabled: true, placement: 'left', height: 72 },
  { key: 'complaint', label: 'Chief Complaint', enabled: true, placement: 'left', height: 92 },
  { key: 'history', label: 'History', enabled: true, placement: 'left', height: 94 },
  { key: 'examination', label: 'Examination', enabled: true, placement: 'left', height: 100 },
  { key: 'diagnosis', label: 'Diagnosis', enabled: true, placement: 'left', height: 82 },
  { key: 'rx', label: 'Medicines', enabled: true, placement: 'right', height: 210 },
  { key: 'investigation', label: 'Investigations', enabled: true, placement: 'right', height: 78 },
  { key: 'advice', label: 'Advice', enabled: true, placement: 'right', height: 86 },
  { key: 'follow_up', label: 'Follow-Up', enabled: true, placement: 'right', height: 54 },
  { key: 'signature', label: 'Signature', enabled: true, placement: 'full', height: 48 },
];

@Component({
  selector: 'app-configuration-workspace',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './configuration-workspace.component.html',
  styleUrls: ['./configuration-workspace.component.scss'],
})
export class ConfigurationWorkspaceComponent {
  private readonly configurationService = inject(ConfigurationService);
  private readonly doctorDirectoryService = inject(DoctorDirectoryService);
  private readonly notificationService = inject(NotificationService);
  private readonly confirmationService = inject(ActionConfirmationService);
  private readonly route = inject(ActivatedRoute);

  workspace: ConfigurationWorkspace | null = null;
  profiles: ConfigurationProfile[] = [];
  doctors: User[] = [];
  readonly context = (this.route.snapshot.data['configurationContext'] as ConfigContext) || 'admin';
  activeType: ConfigType = this.context === 'opd' ? 'doctor_share' : 'invoice_layout';
  editing: ConfigurationProfile | null = null;
  saving = false;
  search = '';
  draggedSectionIndex: number | null = null;
  draggedCanvasSectionKey = '';
  private resizeState: { section: PrescriptionSection; startY: number; startHeight: number } | null = null;
  private columnResizeState: { startX: number; startWidth: number; containerWidth: number } | null = null;

  readonly profileTypes: Array<{ key: ConfigType; label: string; description: string }> = [
    { key: 'doctor_share', label: 'Doctor Share', description: 'Doctor-wise OPD consultation share, follow-up share and preview.' },
    { key: 'prescription_suggestion', label: 'Medicine Suggestions', description: 'Doctor-wise complaints, diagnosis, medicine, investigation and advice shortcuts.' },
    { key: 'prescription_layout', label: 'Prescription Builder', description: 'Doctor-wise drag and drop prescription print sections and display options.' },
    { key: 'invoice_layout', label: 'Invoice Builder', description: 'Invoice, receipt, refund and final bill print options.' },
    { key: 'patient_portal_settings', label: 'Patient Portal', description: 'Patient portal access, downloads, family access and billing visibility.' },
    { key: 'patient_bot_settings', label: 'Patient Bot', description: 'Bot availability, quick replies, guidance and appointment actions.' },
  ];

  readonly opdProfileTypes: ConfigType[] = ['doctor_share', 'prescription_suggestion', 'prescription_layout'];

  shareDraft = this.createShareDraft();
  suggestionDraft = this.createSuggestionDraft();
  layoutDraft = this.createLayoutDraft();
  genericDraft = this.createGenericDraft();
  sharePreviewFee = 1000;
  sharePreviewDiscount = 0;

  constructor() {
    this.doctorDirectoryService.listDoctors().subscribe((doctors) => (this.doctors = doctors));
    this.load();
  }

  get visibleProfileTypes(): Array<{ key: ConfigType; label: string; description: string }> {
    return this.profileTypes.filter((type) => (this.context === 'opd' ? this.opdProfileTypes.includes(type.key) : !this.opdProfileTypes.includes(type.key)));
  }

  get heroKicker(): string {
    return this.context === 'opd' ? 'OPD Configuration' : 'Configuration Center';
  }

  get heroTitle(): string {
    return this.context === 'opd' ? 'Doctor Wise Setup' : 'Hospital Setup';
  }

  get heroSubtitle(): string {
    return this.context === 'opd'
      ? 'Configure doctor share, prescription layout and medicine suggestions with guided controls.'
      : 'Configure hospital-facing settings with readable controls.';
  }

  get filteredProfiles(): ConfigurationProfile[] {
    const query = this.search.trim().toLowerCase();
    return this.profiles
      .filter((item) => item.profile_type === this.activeType)
      .filter((item) => !query || `${item.name} ${item.code} ${item.description || ''} ${this.doctorName(item.target_id)}`.toLowerCase().includes(query));
  }

  get activeTypeMeta() {
    return this.visibleProfileTypes.find((item) => item.key === this.activeType) ?? this.visibleProfileTypes[0] ?? this.profileTypes[0];
  }

  get currentDraft(): BuilderDraft {
    if (this.activeType === 'doctor_share') return this.shareDraft;
    if (this.activeType === 'prescription_suggestion') return this.suggestionDraft;
    if (this.activeType === 'prescription_layout') return this.layoutDraft;
    return this.genericDraft;
  }

  get sharePreview(): { gross: number; net: number; doctor: number; hospital: number } {
    const gross = Number(this.sharePreviewFee || 0);
    const discount = Number(this.sharePreviewDiscount || 0);
    const net = Math.max(0, gross - discount);
    const doctor = this.shareDraft.method === 'fixed'
      ? Math.min(net, Number(this.shareDraft.doctor_share_amount || 0))
      : (net * Number(this.shareDraft.doctor_share_percentage || 0)) / 100;
    return { gross, net, doctor, hospital: Math.max(0, net - doctor) };
  }

  load(): void {
    this.configurationService.workspace().subscribe((workspace) => {
      this.workspace = workspace;
      this.profiles = workspace.profiles;
      if (!this.visibleProfileTypes.some((type) => type.key === this.activeType)) {
        this.activeType = this.visibleProfileTypes[0]?.key || 'invoice_layout';
      }
      this.resetDraft();
    });
  }

  openType(type: ConfigType): void {
    this.activeType = type;
    this.editing = null;
    this.resetDraft();
  }

  edit(profile: ConfigurationProfile): void {
    this.editing = profile;
    const base = {
      code: profile.code,
      name: profile.name,
      description: profile.description || '',
      scope: profile.scope || 'doctor',
      target_type: profile.target_type || '',
      target_id: profile.target_id || '',
      is_default: profile.is_default,
    };
    const payload = profile.payload || {};
    if (profile.profile_type === 'doctor_share') {
      this.shareDraft = { ...this.createShareDraft(), ...base, ...payload } as DoctorShareDraft;
      this.sharePreviewFee = Number(this.shareDraft.consultation_fee || payload['preview_fee'] || 1000);
    } else if (profile.profile_type === 'prescription_suggestion') {
      this.suggestionDraft = { ...this.createSuggestionDraft(), ...base, ...payload } as SuggestionDraft;
    } else if (profile.profile_type === 'prescription_layout') {
      this.layoutDraft = { ...this.createLayoutDraft(), ...base, ...payload, sections: this.normalizeSections(payload['sections'], payload['section_labels']) };
    } else {
      this.genericDraft = { ...this.createGenericDraft(), ...base, ...payload } as GenericDraft;
    }
  }

  duplicate(profile: ConfigurationProfile): void {
    this.edit(profile);
    this.editing = null;
    this.currentDraft.code = `${profile.code}-copy`;
    this.currentDraft.name = `${profile.name} Copy`;
    this.currentDraft.is_default = false;
  }

  resetDraft(): void {
    this.shareDraft = this.createShareDraft();
    this.suggestionDraft = this.createSuggestionDraft();
    this.layoutDraft = this.createLayoutDraft();
    this.genericDraft = this.createGenericDraft();
    this.sharePreviewFee = 1000;
    this.sharePreviewDiscount = 0;
  }

  save(): void {
    const draft = this.currentDraft;
    if (!draft.name.trim()) {
      this.notificationService.error('Please enter a profile name.');
      return;
    }
    if (this.context === 'opd' && !draft.target_id && !draft.is_default) {
      this.notificationService.error('Select a doctor or mark this as the default profile.');
      return;
    }

    this.saving = true;
    const payload = {
      profile_type: this.activeType,
      code: draft.code || this.defaultCode(),
      name: draft.name,
      description: draft.description || null,
      scope: this.context === 'opd' ? 'doctor' : draft.scope || 'hospital',
      target_type: draft.target_id ? 'doctor' : null,
      target_id: draft.target_id || null,
      payload: this.payloadFromDraft(),
      is_default: !!draft.is_default,
      is_active: true,
    };
    const request = this.editing ? this.configurationService.update(this.editing.id, payload) : this.configurationService.create(payload);
    request.subscribe({
      next: () => {
        this.saving = false;
        this.notificationService.success('Configuration saved.');
        this.editing = null;
        this.load();
      },
      error: () => {
        this.saving = false;
      },
    });
  }

  delete(profile: ConfigurationProfile): void {
    if (!this.confirmationService.confirmDestructive(profile.name)) return;
    this.configurationService.delete(profile.id).subscribe(() => {
      this.notificationService.success(`${profile.name} removed.`);
      this.editing = null;
      this.load();
    });
  }

  addListItem(key: keyof SuggestionDraft): void {
    const list = this.suggestionDraft[key];
    if (Array.isArray(list)) list.push('');
  }

  removeListItem(key: keyof SuggestionDraft, index: number): void {
    const list = this.suggestionDraft[key];
    if (Array.isArray(list)) list.splice(index, 1);
  }

  moveSection(from: number, to: number): void {
    if (to < 0 || to >= this.layoutDraft.sections.length) return;
    const [section] = this.layoutDraft.sections.splice(from, 1);
    this.layoutDraft.sections.splice(to, 0, section);
  }

  dragSection(index: number): void {
    this.draggedSectionIndex = index;
  }

  dropSection(index: number): void {
    if (this.draggedSectionIndex === null || this.draggedSectionIndex === index) return;
    this.moveSection(this.draggedSectionIndex, index);
    this.draggedSectionIndex = null;
  }

  doctorName(doctorId?: string | null): string {
    return this.doctors.find((doctor) => doctor.id === doctorId)?.full_name || 'Default';
  }

  getTypeCount(type: ConfigType): number {
    return this.workspace?.counts?.[type] || 0;
  }

  formatCurrency(value: number): string {
    return new Intl.NumberFormat('en-BD', { style: 'currency', currency: 'BDT', maximumFractionDigits: 0 }).format(value);
  }

  get enabledLayoutSections(): PrescriptionSection[] {
    return this.layoutDraft.sections.filter((section) => section.enabled);
  }

  get previewFullSections(): PrescriptionSection[] {
    return this.enabledLayoutSections.filter((section) => section.placement === 'full' && !['header', 'patient', 'signature'].includes(section.key));
  }

  get previewLeftSections(): PrescriptionSection[] {
    return this.enabledLayoutSections.filter((section) => section.placement === 'left' && !['header', 'patient', 'signature'].includes(section.key));
  }

  get previewRightSections(): PrescriptionSection[] {
    return this.enabledLayoutSections.filter((section) => section.placement === 'right' && !['header', 'patient', 'signature'].includes(section.key));
  }

  placementLabel(section: PrescriptionSection): string {
    if (this.layoutDraft.layout === 'single_column') return 'Full width';
    if (section.placement === 'left') return 'Left column';
    if (section.placement === 'right') return 'Right column';
    return 'Full width';
  }

  sectionPlacementClass(section: PrescriptionSection): string {
    if (this.layoutDraft.layout === 'single_column') return 'print-section--full';
    return `print-section--${section.placement || 'full'}`;
  }

  get leftColumnPercent(): number {
    return this.normalizeColumnWidth(this.layoutDraft.left_column_width);
  }

  get rightColumnPercent(): number {
    return 100 - this.leftColumnPercent;
  }

  get previewGridColumns(): string {
    return this.layoutDraft.layout === 'single_column' ? '1fr' : `${this.leftColumnPercent}fr ${this.rightColumnPercent}fr`;
  }

  canvasSections(placement: SectionPlacement): PrescriptionSection[] {
    return this.enabledLayoutSections.filter((section) => section.placement === placement && !['header', 'patient', 'signature'].includes(section.key));
  }

  dragCanvasSection(section: PrescriptionSection): void {
    this.draggedCanvasSectionKey = section.key;
  }

  dropCanvasSection(placement: SectionPlacement): void {
    const section = this.layoutDraft.sections.find((item) => item.key === this.draggedCanvasSectionKey);
    if (!section) return;
    section.placement = placement;
    this.draggedCanvasSectionKey = '';
  }

  startResizeSection(event: PointerEvent, section: PrescriptionSection): void {
    event.preventDefault();
    event.stopPropagation();
    this.resizeState = { section, startY: event.clientY, startHeight: Number(section.height || 80) };
    window.addEventListener('pointermove', this.resizeSection);
    window.addEventListener('pointerup', this.stopResizeSection, { once: true });
  }

  private readonly resizeSection = (event: PointerEvent): void => {
    if (!this.resizeState) return;
    const nextHeight = this.resizeState.startHeight + event.clientY - this.resizeState.startY;
    this.resizeState.section.height = Math.min(Math.max(Math.round(nextHeight), 34), 320);
  };

  private readonly stopResizeSection = (): void => {
    window.removeEventListener('pointermove', this.resizeSection);
    this.resizeState = null;
  };

  startResizeColumns(event: PointerEvent): void {
    if (this.layoutDraft.layout === 'single_column') return;
    const container = (event.currentTarget as HTMLElement).closest('.preview-body-grid') as HTMLElement | null;
    if (!container) return;
    event.preventDefault();
    this.columnResizeState = {
      startX: event.clientX,
      startWidth: this.leftColumnPercent,
      containerWidth: container.getBoundingClientRect().width,
    };
    window.addEventListener('pointermove', this.resizeColumns);
    window.addEventListener('pointerup', this.stopResizeColumns, { once: true });
  }

  private readonly resizeColumns = (event: PointerEvent): void => {
    if (!this.columnResizeState) return;
    const deltaPercent = ((event.clientX - this.columnResizeState.startX) / Math.max(this.columnResizeState.containerWidth, 1)) * 100;
    this.layoutDraft.left_column_width = this.normalizeColumnWidth(this.columnResizeState.startWidth + deltaPercent);
  };

  private readonly stopResizeColumns = (): void => {
    window.removeEventListener('pointermove', this.resizeColumns);
    this.columnResizeState = null;
  };

  private payloadFromDraft(): Record<string, unknown> {
    if (this.activeType === 'doctor_share') {
      const { code, name, description, scope, target_type, target_id, is_default, ...payload } = this.shareDraft;
      return { ...payload, hospital_share_percentage: Math.max(0, 100 - Number(this.shareDraft.doctor_share_percentage || 0)) };
    }
    if (this.activeType === 'prescription_suggestion') {
      const { code, name, description, scope, target_type, target_id, is_default, ...payload } = this.suggestionDraft;
      return {
        ...payload,
        complaints: this.cleanList(this.suggestionDraft.complaints),
        diagnoses: this.cleanList(this.suggestionDraft.diagnoses),
        medicines: this.cleanList(this.suggestionDraft.medicines),
        investigations: this.cleanList(this.suggestionDraft.investigations),
        advice: this.cleanList(this.suggestionDraft.advice),
      };
    }
    if (this.activeType === 'prescription_layout') {
      const { code, name, description, scope, target_type, target_id, is_default, ...payload } = this.layoutDraft;
      return {
        ...payload,
        sections: this.enabledLayoutSections.map((item) => item.key),
        section_labels: this.layoutDraft.sections,
        section_placements: this.enabledLayoutSections.map((item) => ({ key: item.key, placement: item.placement })),
      };
    }
    const { code, name, description, scope, target_type, target_id, is_default, ...payload } = this.genericDraft;
    return payload;
  }

  private createBaseDraft(): BuilderDraft {
    return {
      code: this.defaultCode(),
      name: `New ${this.activeTypeMeta.label}`,
      description: this.activeTypeMeta.description,
      scope: this.context === 'opd' ? 'doctor' : 'hospital',
      target_type: '',
      target_id: '',
      is_default: false,
    };
  }

  private createShareDraft(): DoctorShareDraft {
    return {
      ...this.createBaseDraft(),
      method: 'percentage',
      consultation_fee: 1000,
      doctor_share_percentage: 70,
      doctor_share_amount: 0,
      follow_up_share_percentage: 50,
      hospital_share_percentage: 30,
      applies_to_follow_up: true,
      notes: '',
    };
  }

  private createSuggestionDraft(): SuggestionDraft {
    return {
      ...this.createBaseDraft(),
      complaints: ['Fever for 3 days', 'Cough and cold', 'Abdominal pain'],
      diagnoses: ['Viral fever', 'URTI', 'Gastritis'],
      medicines: ['Napa 500 mg - 1+1+1 after meal for 3 days', 'Antacid - before meal for 5 days'],
      investigations: ['CBC', 'Urine R/E'],
      advice: ['Drink plenty of water', 'Take rest', 'Avoid oily food'],
      follow_up_days: 7,
    };
  }

  private createLayoutDraft(): LayoutDraft {
    return {
      ...this.createBaseDraft(),
      paper_size: 'A5',
      layout: 'two_column',
      font_size: 11,
      left_column_width: 38,
      show_logo: true,
      show_barcode: true,
      show_qr: true,
      footer_note: 'Please bring this prescription on follow-up.',
      sections: SECTION_LIBRARY.map((section) => ({ ...section })),
    };
  }

  private createGenericDraft(): GenericDraft {
    return {
      ...this.createBaseDraft(),
      enabled: true,
      allow_appointment_booking: true,
      allow_online_payment: false,
      allow_family_access: true,
      allow_document_download: true,
      show_billing_details: true,
      footer_note: 'Thank you.',
    };
  }

  private cleanList(value: string[]): string[] {
    return value.map((item) => item.trim()).filter(Boolean);
  }

  private normalizeSections(value: unknown, labelsValue?: unknown): PrescriptionSection[] {
    const keys = Array.isArray(value) ? value.map(String) : SECTION_LIBRARY.map((section) => section.key);
    const savedLabels = Array.isArray(labelsValue) ? labelsValue as Array<Partial<PrescriptionSection> & { key?: string }> : [];
    const savedByKey = new Map(savedLabels.filter((item) => item.key).map((item) => [String(item.key), item]));
    const ordered = keys.map((key) => {
      const librarySection = SECTION_LIBRARY.find((section) => section.key === key) || { key, label: key, enabled: true, placement: 'full' as SectionPlacement, height: 80 };
      const saved = savedByKey.get(key);
      return { ...librarySection, ...saved, key, enabled: true, placement: this.normalizePlacement(saved?.placement || librarySection.placement), height: this.normalizeHeight(saved?.height || librarySection.height) };
    });
    const missing = SECTION_LIBRARY.filter((section) => !keys.includes(section.key)).map((section) => ({ ...section, enabled: false }));
    return [...ordered, ...missing];
  }

  private normalizePlacement(value: unknown): SectionPlacement {
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

  private defaultCode(): string {
    return `${this.activeType}-${Date.now().toString().slice(-5)}`;
  }
}
