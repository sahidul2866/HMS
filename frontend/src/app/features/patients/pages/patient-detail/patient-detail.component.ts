import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';

import { PERMISSIONS } from '../../../../core/constants/permissions';
import { NotificationService } from '../../../../core/services/notification.service';
import { SessionService } from '../../../../core/services/session.service';
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
  readonly sessionService = inject(SessionService);
  readonly permissions = PERMISSIONS;

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

  openBilling(): void {
    if (this.history) {
      void this.router.navigate(['/billing/create'], { queryParams: { patientId: this.history.patient.id } });
    }
  }

  openIpdAdmission(): void {
    if (this.history) {
      void this.router.navigate(['/ipd/admit'], { queryParams: { patientId: this.history.patient.id } });
    }
  }

  openOpdRegistration(): void {
    if (this.history) {
      void this.router.navigate(['/opd/register'], { queryParams: { patientId: this.history.patient.id } });
    }
  }

  openVisitBilling(visit: PatientHistoryOPDVisit): void {
    if (this.history) {
      void this.router.navigate(['/billing/create'], { queryParams: { patientId: this.history.patient.id, opdVisitId: visit.id } });
    }
  }

  formatCurrency(value: string | number): string {
    return new Intl.NumberFormat('en-BD', {
      style: 'currency',
      currency: 'BDT',
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
