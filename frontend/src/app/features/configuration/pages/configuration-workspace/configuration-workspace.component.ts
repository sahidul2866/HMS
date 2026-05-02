import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';

import { NotificationService } from '../../../../core/services/notification.service';
import { ConfigurationProfile, ConfigurationService, ConfigurationWorkspace } from '../../services/configuration.service';

type ConfigType = 'doctor_share' | 'prescription_suggestion' | 'prescription_layout' | 'invoice_layout' | 'patient_portal_settings' | 'patient_bot_settings';

@Component({
  selector: 'app-configuration-workspace',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule],
  templateUrl: './configuration-workspace.component.html',
  styleUrls: ['./configuration-workspace.component.scss'],
})
export class ConfigurationWorkspaceComponent {
  private readonly fb = inject(FormBuilder);
  private readonly configurationService = inject(ConfigurationService);
  private readonly notificationService = inject(NotificationService);

  workspace: ConfigurationWorkspace | null = null;
  profiles: ConfigurationProfile[] = [];
  activeType: ConfigType = 'doctor_share';
  editing: ConfigurationProfile | null = null;
  saving = false;
  search = '';

  readonly profileTypes: Array<{ key: ConfigType; label: string; description: string }> = [
    { key: 'doctor_share', label: 'Doctor Fee & Share', description: 'Consultation fee split, hospital share, follow-up and corporate rules.' },
    { key: 'prescription_suggestion', label: 'Prescription Suggestions', description: 'Doctor favorites, templates, medicine, advice, investigation and follow-up suggestions.' },
    { key: 'prescription_layout', label: 'Prescription Builder', description: 'Logo, header, clinical sections, QR/barcode, footer, paper size and section order.' },
    { key: 'invoice_layout', label: 'Invoice Layout Builder', description: 'Invoice, receipt, advance, refund and final bill print structures.' },
    { key: 'patient_portal_settings', label: 'Patient Portal', description: 'Patient portal access, document download, family access, billing visibility and portal branding.' },
    { key: 'patient_bot_settings', label: 'Patient Bot', description: 'Gemini usage, safety message, quick replies, intake flow, diet/report guidance and appointment actions.' },
  ];

  readonly form = this.fb.group({
    code: ['', Validators.required],
    name: ['', Validators.required],
    description: [''],
    scope: ['hospital', Validators.required],
    target_type: [''],
    is_default: [false],
    payload: ['{}', Validators.required],
  });

  readonly sharePreviewForm = this.fb.group({
    consultationFee: [1000],
    discount: [0],
  });

  constructor() {
    this.load();
  }

  load(): void {
    this.configurationService.workspace().subscribe((workspace) => {
      this.workspace = workspace;
      this.profiles = workspace.profiles;
      if (!this.activeProfile) {
        this.openType(this.activeType);
      }
    });
  }

  get filteredProfiles(): ConfigurationProfile[] {
    const query = this.search.trim().toLowerCase();
    return this.profiles
      .filter((item) => item.profile_type === this.activeType)
      .filter((item) => !query || `${item.name} ${item.code} ${item.description || ''}`.toLowerCase().includes(query));
  }

  get activeProfile(): ConfigurationProfile | null {
    return this.filteredProfiles[0] ?? null;
  }

  get activeTypeMeta() {
    return this.profileTypes.find((item) => item.key === this.activeType) ?? this.profileTypes[0];
  }

  get sharePreview(): { gross: number; net: number; doctor: number; hospital: number } {
    const payload = this.payloadObject(this.activeProfile);
    const gross = Number(this.sharePreviewForm.getRawValue().consultationFee || 0);
    const discount = Number(this.sharePreviewForm.getRawValue().discount || 0);
    const net = Math.max(0, gross - discount);
    let doctor = 0;
    if (payload['method'] === 'fixed') {
      doctor = Math.min(net, Number(payload['doctor_share_amount'] || 0));
    } else {
      doctor = (net * Number(payload['doctor_share_percentage'] || 0)) / 100;
    }
    return { gross, net, doctor, hospital: Math.max(0, net - doctor) };
  }

  openType(type: ConfigType): void {
    this.activeType = type;
    this.editing = null;
    this.resetForm();
  }

  edit(profile: ConfigurationProfile): void {
    this.editing = profile;
    this.form.reset({
      code: profile.code,
      name: profile.name,
      description: profile.description || '',
      scope: profile.scope,
      target_type: profile.target_type || '',
      is_default: profile.is_default,
      payload: JSON.stringify(profile.payload || {}, null, 2),
    });
  }

  duplicate(profile: ConfigurationProfile): void {
    this.editing = null;
    this.form.reset({
      code: `${profile.code}-copy`,
      name: `${profile.name} Copy`,
      description: profile.description || '',
      scope: profile.scope,
      target_type: profile.target_type || '',
      is_default: false,
      payload: JSON.stringify(profile.payload || {}, null, 2),
    });
  }

  resetForm(): void {
    this.form.reset({
      code: this.defaultCode(),
      name: this.defaultName(),
      description: this.activeTypeMeta.description,
      scope: 'hospital',
      target_type: '',
      is_default: false,
      payload: JSON.stringify(this.defaultPayload(), null, 2),
    });
  }

  save(): void {
    if (this.form.invalid || this.saving) {
      this.form.markAllAsTouched();
      return;
    }
    let payloadObject: Record<string, unknown>;
    try {
      payloadObject = JSON.parse(this.form.getRawValue().payload || '{}');
    } catch {
      this.notificationService.error('Payload JSON is invalid.');
      return;
    }
    this.saving = true;
    const raw = this.form.getRawValue();
    const payload = {
      profile_type: this.activeType,
      code: raw.code,
      name: raw.name,
      description: raw.description || null,
      scope: raw.scope || 'hospital',
      target_type: raw.target_type || null,
      target_id: null,
      payload: payloadObject,
      is_default: !!raw.is_default,
      is_active: true,
    };
    const request = this.editing ? this.configurationService.update(this.editing.id, payload) : this.configurationService.create(payload);
    request.subscribe({
      next: () => {
        this.saving = false;
        this.notificationService.success('Configuration profile saved.');
        this.resetForm();
        this.load();
      },
      error: () => {
        this.saving = false;
      },
    });
  }

  delete(profile: ConfigurationProfile): void {
    if (!window.confirm(`Delete ${profile.name}?`)) {
      return;
    }
    this.configurationService.delete(profile.id).subscribe(() => {
      this.notificationService.success('Configuration profile removed.');
      this.load();
    });
  }

  payloadObject(profile: ConfigurationProfile | null): Record<string, unknown> {
    return (profile?.payload || {}) as Record<string, unknown>;
  }

  getSections(profile: ConfigurationProfile | null): string[] {
    const sections = this.payloadObject(profile)['sections'];
    return Array.isArray(sections) ? sections.map(String) : [];
  }

  payloadListLabel(key: string): string {
    const value = this.payloadObject(this.activeProfile)[key];
    if (Array.isArray(value)) {
      return value.length ? value.map(String).join(', ') : 'Not configured';
    }
    return value ? String(value) : 'Not configured';
  }

  getTypeCount(type: ConfigType): number {
    return this.workspace?.counts?.[type] || 0;
  }

  formatCurrency(value: number): string {
    return new Intl.NumberFormat('en-BD', { style: 'currency', currency: 'BDT' }).format(value);
  }

  private defaultCode(): string {
    return `${this.activeType}-${Date.now().toString().slice(-5)}`;
  }

  private defaultName(): string {
    return `New ${this.activeTypeMeta.label}`;
  }

  private defaultPayload(): Record<string, unknown> {
    if (this.activeType === 'doctor_share') {
      return { method: 'percentage', doctor_share_percentage: 70, hospital_share_percentage: 30, follow_up_share_percentage: 50, preview_fee: 1000 };
    }
    if (this.activeType === 'prescription_suggestion') {
      return { complaints: [''], diagnoses: [''], medicines: [''], investigations: [''], advice: [''], follow_up_days: 7 };
    }
    if (this.activeType === 'prescription_layout') {
      return { paper_size: 'A5', layout: 'two_column', font_size: 11, show_logo: true, show_barcode: true, sections: ['header', 'patient', 'complaint', 'diagnosis', 'rx', 'advice', 'follow_up', 'signature'] };
    }
    if (this.activeType === 'patient_portal_settings') {
      return {
        enabled: true,
        allow_appointment_booking: true,
        allow_online_payment: false,
        allow_profile_update: true,
        allow_family_access: true,
        allow_document_download: true,
        show_billing_details: true,
        show_ipd_running_bill: true,
        show_doctor_notes: false,
        show_diagnosis: true,
        require_profile_update_approval: true,
        theme: { logo: 'default', banner: 'care dashboard', accent_color: '#0f766e' },
        dashboard_widgets: ['appointments', 'prescriptions', 'reports', 'billing', 'documents'],
      };
    }
    if (this.activeType === 'patient_bot_settings') {
      return {
        enabled: true,
        gemini_enabled: true,
        gemini_model: 'gemini-2.5-flash',
        max_gemini_calls_per_patient_per_day: 5,
        diet_guidance_enabled: true,
        report_explanation_enabled: true,
        prescription_explanation_enabled: true,
        appointment_booking_enabled: true,
        emergency_message: 'Based on what you shared, it may be safer to seek urgent medical care now. Please contact emergency services or visit the nearest emergency department.',
        quick_replies: ['I have symptoms', 'Find a doctor', 'Diet guidance', 'Understand report', 'Book appointment'],
      };
    }
    return { template_for: 'opd', paper_size: 'A5', show_logo: true, show_qr: true, columns: ['service', 'qty', 'rate', 'discount', 'total'], footer_note: 'Thank you.' };
  }
}
