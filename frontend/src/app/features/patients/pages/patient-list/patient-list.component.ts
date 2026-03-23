import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { NotificationService } from '../../../../core/services/notification.service';
import { UiStateService } from '../../../../core/services/ui-state.service';
import { HasPermissionDirective } from '../../../../shared/directives/has-permission.directive';
import { PatientService } from '../../services/patient.service';
import { Patient, PatientClinicalHistory } from '../../models/patient.models';

@Component({
  selector: 'app-patient-list',
  standalone: true,
  imports: [CommonModule, RouterLink, HasPermissionDirective],
  templateUrl: './patient-list.component.html',
})
export class PatientListComponent {
  private static readonly STATE_KEY = 'ui-state:patients:list';
  private readonly patientService = inject(PatientService);
  private readonly notificationService = inject(NotificationService);
  private readonly uiStateService = inject(UiStateService);

  patients: Patient[] = [];
  loading = true;
  selectedHistory: PatientClinicalHistory | null = null;
  historyLoading = false;
  private selectedHistoryPatientId: string | null = null;

  constructor() {
    const restoredState = this.uiStateService.load<{ selectedHistoryPatientId?: string | null }>(PatientListComponent.STATE_KEY);
    this.selectedHistoryPatientId = restoredState?.selectedHistoryPatientId ?? null;

    this.patientService.list().subscribe({
      next: (patients) => {
        this.patients = patients;
        this.loading = false;
        if (this.selectedHistoryPatientId) {
          const patient = patients.find((item) => item.id === this.selectedHistoryPatientId);
          if (patient) {
            this.openHistory(patient);
          }
        }
      },
      error: () => {
        this.loading = false;
      },
    });
  }

  openHistory(patient: Patient): void {
    this.historyLoading = true;
    this.selectedHistoryPatientId = patient.id;
    this.persistState();
    this.patientService.getHistory(patient.id).subscribe({
      next: (history) => {
        this.selectedHistory = history;
        this.historyLoading = false;
      },
      error: () => {
        this.historyLoading = false;
        this.notificationService.error(`Could not load history for ${patient.first_name} ${patient.last_name}.`);
      },
    });
  }

  closeHistory(): void {
    this.selectedHistory = null;
    this.selectedHistoryPatientId = null;
    this.persistState();
  }

  formatCurrency(value: string | number): string {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(Number(value));
  }

  private persistState(): void {
    this.uiStateService.save(PatientListComponent.STATE_KEY, {
      selectedHistoryPatientId: this.selectedHistoryPatientId,
    });
  }
}
