import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { NotificationService } from '../../../../core/services/notification.service';
import { PatientIdCardTemplate } from '../../models/patient.models';
import { PatientService } from '../../services/patient.service';

@Component({
  selector: 'app-patient-id-card-settings',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './patient-id-card-settings.component.html',
  styleUrls: ['./patient-id-card-settings.component.scss'],
})
export class PatientIdCardSettingsComponent {
  private readonly patientService = inject(PatientService);
  private readonly notifications = inject(NotificationService);

  saving = false;
  template: PatientIdCardTemplate = {
    card_size: '85.6x54mm',
    logo_url: '',
    header: 'Hospital Patient ID',
    footer: 'Please present this card at every hospital visit.',
    code_type: 'code39',
    theme_color: '#0f766e',
    show_phone: true,
    show_emergency_contact: true,
    show_dob: true,
    show_issue_date: true,
    print_layout: 'standard-card',
  };

  constructor() {
    this.patientService.getIdCardTemplate().subscribe((template) => (this.template = template));
  }

  save(): void {
    if (this.saving) return;
    this.saving = true;
    this.patientService.updateIdCardTemplate(this.template).subscribe({
      next: (template) => {
        this.template = template;
        this.saving = false;
        this.notifications.success('Patient ID card template saved.');
      },
      error: () => (this.saving = false),
    });
  }
}

