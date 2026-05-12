import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { NotificationService } from '../../../../core/services/notification.service';
import { IPDBed, IPDSettings } from '../../models/ipd.models';
import { IPDService } from '../../services/ipd.service';

@Component({
  selector: 'app-ipd-settings',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './ipd-settings.component.html',
  styleUrls: ['./ipd-settings.component.scss'],
})
export class IPDSettingsComponent {
  private readonly fb = inject(FormBuilder);
  private readonly ipdService = inject(IPDService);
  private readonly notificationService = inject(NotificationService);

  beds: IPDBed[] = [];
  settings: IPDSettings | null = null;
  activeTab: 'beds' | 'admission' | 'assignment' | 'handover' | 'clinical' | 'discharge' | 'permissions' = 'beds';
  savingSettings = false;
  settingsError = '';

  readonly bedForm = this.fb.group({
    ward_name: ['Ward A', Validators.required],
    bed_number: ['', Validators.required],
    bed_type: ['General', Validators.required],
    daily_rate: [0, Validators.required],
    note: [''],
  });

  readonly settingsForm = this.fb.group({
    ward_types: [''],
    room_types: [''],
    bed_types: [''],
    bed_statuses: [''],
    cleaning_statuses: [''],
    critical_care_categories: [''],
    default_bed_charges: ['{}'],
    admission_sources: [''],
    admission_types: [''],
    required_admission_fields: [''],
    admission_number_format: ['IPD-{YYYY}{MM}{DD}-{SEQ4}', Validators.required],
    department_admission_rules: ['{}'],
    payment_type_rules: ['{}'],
    insurance_corporate_rules: ['{}'],
    doctor_assignment_types: [''],
    nurse_assignment_types: [''],
    max_patient_load_doctor: [20, Validators.required],
    max_patient_load_nurse: [8, Validators.required],
    department_staff_rules: ['{}'],
    shift_assignment_rules: ['{}'],
    on_call_assignment_rules: ['{}'],
    handover_templates: ['[]'],
    required_handover_fields: ['summary'],
    shift_handover_timings: ['{}'],
    require_handover_acknowledgment: [true],
    handover_escalation_minutes: [30],
    doctor_note_templates: ['[]'],
    nursing_note_templates: ['[]'],
    vitals_config: ['{}'],
    intake_output_settings: ['{}'],
    care_plan_templates: ['[]'],
    procedure_note_templates: ['[]'],
    discharge_approval_levels: [''],
    required_discharge_summary_fields: [''],
    clearance_requirements: ['{}'],
    billing_clearance_rules: ['{}'],
    pharmacy_clearance_rules: ['{}'],
    lab_radiology_pending_order_rules: ['{}'],
    follow_up_requirements: ['{}'],
    role_permission_notes: ['{}'],
  });

  constructor() {
    this.loadBeds();
    this.loadSettings();
  }

  loadBeds(): void {
    this.ipdService.listBeds().subscribe((beds) => (this.beds = beds));
  }

  loadSettings(): void {
    this.ipdService.getSettings().subscribe((settings) => {
      this.settings = settings;
      this.patchSettingsForm(settings);
    });
  }

  submitBed(): void {
    if (this.bedForm.invalid) {
      this.bedForm.markAllAsTouched();
      return;
    }
    this.ipdService.createBed(this.bedForm.getRawValue() as never).subscribe((bed) => {
      this.notificationService.success(`Bed ${bed.ward_name} / ${bed.bed_number} created.`);
      this.bedForm.reset({
        ward_name: this.bedForm.getRawValue().ward_name || 'Ward A',
        bed_number: '',
        bed_type: this.bedForm.getRawValue().bed_type || 'General',
        daily_rate: 0,
        note: '',
      });
      this.loadBeds();
    });
  }

  get wardOptions(): string[] {
    return [...new Set(this.beds.map((bed) => bed.ward_name).filter(Boolean))].sort((a, b) => a.localeCompare(b));
  }

  get bedTypeOptions(): string[] {
    return [...new Set([...(this.settings?.bed_types || []), ...this.beds.map((bed) => bed.bed_type).filter(Boolean)])].sort((a, b) => a.localeCompare(b));
  }

  saveSettings(): void {
    if (!this.settings || this.settingsForm.invalid || this.savingSettings) {
      this.settingsForm.markAllAsTouched();
      return;
    }
    this.settingsError = '';
    let payload: IPDSettings;
    try {
      payload = this.buildSettingsPayload();
    } catch (error) {
      this.settingsError = error instanceof Error ? error.message : 'Invalid settings JSON';
      return;
    }
    this.savingSettings = true;
    this.ipdService.updateSettings(payload).subscribe({
      next: (settings) => {
        this.savingSettings = false;
        this.settings = settings;
        this.patchSettingsForm(settings);
        this.notificationService.success('IPD settings saved.');
      },
      error: () => {
        this.savingSettings = false;
      },
    });
  }

  private patchSettingsForm(settings: IPDSettings): void {
    this.settingsForm.patchValue({
      ward_types: this.join(settings.ward_types),
      room_types: this.join(settings.room_types),
      bed_types: this.join(settings.bed_types),
      bed_statuses: this.join(settings.bed_statuses),
      cleaning_statuses: this.join(settings.cleaning_statuses),
      critical_care_categories: this.join(settings.critical_care_categories),
      default_bed_charges: this.pretty(settings.default_bed_charges),
      admission_sources: this.join(settings.admission_sources),
      admission_types: this.join(settings.admission_types),
      required_admission_fields: this.join(settings.required_admission_fields),
      admission_number_format: settings.admission_number_format,
      department_admission_rules: this.pretty(settings.department_admission_rules),
      payment_type_rules: this.pretty(settings.payment_type_rules),
      insurance_corporate_rules: this.pretty(settings.insurance_corporate_rules),
      doctor_assignment_types: this.join(settings.doctor_assignment_types),
      nurse_assignment_types: this.join(settings.nurse_assignment_types),
      max_patient_load_doctor: settings.max_patient_load_doctor,
      max_patient_load_nurse: settings.max_patient_load_nurse,
      department_staff_rules: this.pretty(settings.department_staff_rules),
      shift_assignment_rules: this.pretty(settings.shift_assignment_rules),
      on_call_assignment_rules: this.pretty(settings.on_call_assignment_rules),
      handover_templates: this.pretty(settings.handover_templates),
      required_handover_fields: this.join(settings.required_handover_fields),
      shift_handover_timings: this.pretty(settings.shift_handover_timings),
      require_handover_acknowledgment: settings.require_handover_acknowledgment,
      handover_escalation_minutes: settings.handover_escalation_minutes,
      doctor_note_templates: this.pretty(settings.doctor_note_templates),
      nursing_note_templates: this.pretty(settings.nursing_note_templates),
      vitals_config: this.pretty(settings.vitals_config),
      intake_output_settings: this.pretty(settings.intake_output_settings),
      care_plan_templates: this.pretty(settings.care_plan_templates),
      procedure_note_templates: this.pretty(settings.procedure_note_templates),
      discharge_approval_levels: this.join(settings.discharge_approval_levels),
      required_discharge_summary_fields: this.join(settings.required_discharge_summary_fields),
      clearance_requirements: this.pretty(settings.clearance_requirements),
      billing_clearance_rules: this.pretty(settings.billing_clearance_rules),
      pharmacy_clearance_rules: this.pretty(settings.pharmacy_clearance_rules),
      lab_radiology_pending_order_rules: this.pretty(settings.lab_radiology_pending_order_rules),
      follow_up_requirements: this.pretty(settings.follow_up_requirements),
      role_permission_notes: this.pretty(settings.role_permission_notes),
    });
  }

  private buildSettingsPayload(): IPDSettings {
    const value = this.settingsForm.getRawValue();
    return {
      ...(this.settings as IPDSettings),
      ward_types: this.split(value.ward_types),
      room_types: this.split(value.room_types),
      bed_types: this.split(value.bed_types),
      bed_statuses: this.split(value.bed_statuses),
      cleaning_statuses: this.split(value.cleaning_statuses),
      critical_care_categories: this.split(value.critical_care_categories),
      default_bed_charges: this.parseObject(value.default_bed_charges, 'Default bed charges') as Record<string, string | number>,
      admission_sources: this.split(value.admission_sources),
      admission_types: this.split(value.admission_types),
      required_admission_fields: this.split(value.required_admission_fields),
      admission_number_format: value.admission_number_format || 'IPD-{YYYY}{MM}{DD}-{SEQ4}',
      department_admission_rules: this.parseObject(value.department_admission_rules, 'Department admission rules'),
      payment_type_rules: this.parseObject(value.payment_type_rules, 'Payment type rules'),
      insurance_corporate_rules: this.parseObject(value.insurance_corporate_rules, 'Insurance/corporate rules'),
      doctor_assignment_types: this.split(value.doctor_assignment_types),
      nurse_assignment_types: this.split(value.nurse_assignment_types),
      max_patient_load_doctor: Number(value.max_patient_load_doctor || 20),
      max_patient_load_nurse: Number(value.max_patient_load_nurse || 8),
      department_staff_rules: this.parseObject(value.department_staff_rules, 'Department staff rules'),
      shift_assignment_rules: this.parseObject(value.shift_assignment_rules, 'Shift assignment rules'),
      on_call_assignment_rules: this.parseObject(value.on_call_assignment_rules, 'On-call assignment rules'),
      handover_templates: this.parseArray(value.handover_templates, 'Handover templates'),
      required_handover_fields: this.split(value.required_handover_fields),
      shift_handover_timings: this.parseObject(value.shift_handover_timings, 'Shift handover timings') as Record<string, string>,
      require_handover_acknowledgment: !!value.require_handover_acknowledgment,
      handover_escalation_minutes: Number(value.handover_escalation_minutes || 0),
      doctor_note_templates: this.parseArray(value.doctor_note_templates, 'Doctor note templates'),
      nursing_note_templates: this.parseArray(value.nursing_note_templates, 'Nursing note templates'),
      vitals_config: this.parseObject(value.vitals_config, 'Vitals configuration'),
      intake_output_settings: this.parseObject(value.intake_output_settings, 'Intake/output settings'),
      care_plan_templates: this.parseArray(value.care_plan_templates, 'Care plan templates'),
      procedure_note_templates: this.parseArray(value.procedure_note_templates, 'Procedure note templates'),
      discharge_approval_levels: this.split(value.discharge_approval_levels),
      required_discharge_summary_fields: this.split(value.required_discharge_summary_fields),
      clearance_requirements: this.parseObject(value.clearance_requirements, 'Clearance requirements') as Record<string, boolean>,
      billing_clearance_rules: this.parseObject(value.billing_clearance_rules, 'Billing clearance rules'),
      pharmacy_clearance_rules: this.parseObject(value.pharmacy_clearance_rules, 'Pharmacy clearance rules'),
      lab_radiology_pending_order_rules: this.parseObject(value.lab_radiology_pending_order_rules, 'Lab/radiology rules'),
      follow_up_requirements: this.parseObject(value.follow_up_requirements, 'Follow-up requirements'),
      role_permission_notes: this.parseObject(value.role_permission_notes, 'Role permission notes') as Record<string, string[]>,
    };
  }

  private split(value: string | null | undefined): string[] {
    return String(value || '').split(',').map((item) => item.trim()).filter(Boolean);
  }

  private join(value: string[] | null | undefined): string {
    return (value || []).join(', ');
  }

  private pretty(value: unknown): string {
    return JSON.stringify(value ?? {}, null, 2);
  }

  private parseObject(value: string | null | undefined, label: string): Record<string, unknown> {
    const parsed = this.parseJson(value, label);
    if (!parsed || Array.isArray(parsed) || typeof parsed !== 'object') {
      throw new Error(`${label} must be a JSON object.`);
    }
    return parsed as Record<string, unknown>;
  }

  private parseArray(value: string | null | undefined, label: string): Array<Record<string, unknown>> {
    const parsed = this.parseJson(value, label);
    if (!Array.isArray(parsed)) {
      throw new Error(`${label} must be a JSON array.`);
    }
    return parsed as Array<Record<string, unknown>>;
  }

  private parseJson(value: string | null | undefined, label: string): unknown {
    try {
      return JSON.parse(value || '{}');
    } catch {
      throw new Error(`${label} contains invalid JSON.`);
    }
  }
}
