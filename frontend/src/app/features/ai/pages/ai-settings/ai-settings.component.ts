import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { StaffBotAdminSetting, StaffBotService } from '../../../../core/services/staff-bot.service';

@Component({
  selector: 'app-ai-settings',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './ai-settings.component.html',
  styleUrls: ['./ai-settings.component.scss'],
})
export class AiSettingsComponent {
  private readonly staffBot = inject(StaffBotService);

  settings: StaffBotAdminSetting[] = [];
  message = '';
  form = {
    setting_key: 'global',
    enabled: true,
    greeting_message: 'Hi! I’m your Staff Assistant. Ask about OPD, IPD beds, pharmacy stock, billing dues, appointments, or patients.',
    audit_logging: true,
    require_confirmation_for_sensitive_actions: true,
    patients: true,
    opd: true,
    ipd: true,
    er: true,
    billing: true,
    pharmacy: true,
    laboratory: true,
    radiology: true,
    inventory: true,
    blood_bank: true,
    hr: true,
    payroll: true,
    accounting: true,
    reports: true,
  };

  constructor() {
    this.load();
  }

  load(): void {
    this.staffBot.listAdminSettings().subscribe({
      next: (settings) => (this.settings = settings),
      error: (error) => (this.message = error?.error?.message || 'Unable to load AI settings'),
    });
  }

  save(): void {
    const setting_value = {
      enabled: this.form.enabled,
      greeting_message: this.form.greeting_message,
      audit_logging: this.form.audit_logging,
      module_availability: {
        patients: this.form.patients,
        opd: this.form.opd,
        ipd: this.form.ipd,
        er: this.form.er,
        billing: this.form.billing,
        pharmacy: this.form.pharmacy,
        laboratory: this.form.laboratory,
        radiology: this.form.radiology,
        inventory: this.form.inventory,
        blood_bank: this.form.blood_bank,
        hr: this.form.hr,
        payroll: this.form.payroll,
        accounting: this.form.accounting,
        reports: this.form.reports,
      },
      action_rules: {
        require_confirmation_for_sensitive_actions: this.form.require_confirmation_for_sensitive_actions,
      },
    };
    this.staffBot.saveAdminSetting({ setting_key: this.form.setting_key, setting_value }).subscribe({
      next: () => {
        this.message = 'AI assistant settings saved';
        this.load();
      },
      error: (error) => (this.message = error?.error?.message || 'Unable to save AI settings'),
    });
  }
}
