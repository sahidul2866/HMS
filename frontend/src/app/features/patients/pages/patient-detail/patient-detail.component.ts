import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';

import { NotificationService } from '../../../../core/services/notification.service';
import { PatientClinicalHistory, PatientHistoryOPDVisit } from '../../models/patient.models';
import { PatientService } from '../../services/patient.service';

@Component({
  selector: 'app-patient-detail',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './patient-detail.component.html',
  styleUrls: ['./patient-detail.component.scss'],
})
export class PatientDetailComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly patientService = inject(PatientService);
  private readonly notificationService = inject(NotificationService);

  historyLoading = true;
  history: PatientClinicalHistory | null = null;

  constructor() {
    this.route.paramMap.subscribe((params) => {
      const patientId = params.get('patientId');
      if (!patientId) {
        void this.router.navigate(['/patients']);
        return;
      }
      this.loadHistory(patientId);
    });
  }

  openList(): void {
    void this.router.navigate(['/patients']);
  }

  formatCurrency(value: string | number): string {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(Number(value));
  }

  getVisitDiagnosis(visit: PatientHistoryOPDVisit): string {
    return visit.final_diagnosis || visit.provisional_diagnosis || visit.chief_complaint || '-';
  }

  getVisitOrderCount(visit: PatientHistoryOPDVisit, type: string): number {
    return visit.orders.filter((order) => order.order_type === type).length;
  }

  getPendingFollowUps(): number {
    return this.history?.appointments.filter((appointment) => ['scheduled', 'confirmed'].includes(appointment.status)).length ?? 0;
  }

  private loadHistory(patientId: string): void {
    this.historyLoading = true;
    this.patientService.getHistory(patientId).subscribe({
      next: (history) => {
        this.history = history;
        this.historyLoading = false;
      },
      error: () => {
        this.historyLoading = false;
        this.notificationService.error('Could not load patient history.');
        void this.router.navigate(['/patients']);
      },
    });
  }
}
