import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';

import { PERMISSIONS } from '../../../../core/constants/permissions';
import { NotificationService } from '../../../../core/services/notification.service';
import { SessionService } from '../../../../core/services/session.service';
import { PatientContextPanelComponent } from '../../../../shared/components/patient-context-panel/patient-context-panel.component';
import { code39Svg, printScanLabel } from '../../../../shared/utils/scan-print.utils';
import { PatientClinicalHistory, PatientHistoryOPDVisit, PatientIdCard } from '../../models/patient.models';
import { PatientService } from '../../services/patient.service';

@Component({
  selector: 'app-patient-detail',
  standalone: true,
  imports: [CommonModule, PatientContextPanelComponent],
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
  idCard: PatientIdCard | null = null;
  idCardPreviewOpen = false;
  idCardLoading = false;

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

  previewIdCard(): void {
    if (!this.history || this.idCardLoading) return;
    this.idCardLoading = true;
    this.patientService.getIdCard(this.history.patient.id).subscribe({
      next: (card) => {
        this.idCard = card;
        this.idCardPreviewOpen = true;
        this.idCardLoading = false;
      },
      error: () => {
        this.idCardLoading = false;
        this.notificationService.error('Could not load patient ID card.');
      },
    });
  }

  generateIdCard(): void {
    if (!this.history || this.idCardLoading) return;
    this.idCardLoading = true;
    this.patientService.generateIdCard(this.history.patient.id).subscribe({
      next: (card) => {
        this.idCard = card;
        this.idCardPreviewOpen = true;
        this.idCardLoading = false;
        this.notificationService.success('Patient ID card generated.');
      },
      error: () => (this.idCardLoading = false),
    });
  }

  printIdCard(reprint = false): void {
    if (!this.history || this.idCardLoading) return;
    this.idCardLoading = true;
    this.patientService.printIdCard(this.history.patient.id, reprint).subscribe({
      next: (card) => {
        this.idCard = card;
        this.idCardLoading = false;
        this.renderPatientCardPrint(card);
      },
      error: () => (this.idCardLoading = false),
    });
  }

  closeIdCardPreview(): void {
    this.idCardPreviewOpen = false;
  }

  barcodeSvg(): string {
    return this.idCard ? code39Svg(this.idCard.scan_code) : '';
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

  private renderPatientCardPrint(card: PatientIdCard): void {
    const patient = card.patient;
    printScanLabel({
      kind: 'card',
      title: card.hospital_name,
      subtitle: card.template.header,
      code: card.scan_code,
      logoUrl: card.template.logo_url,
      themeColor: card.template.theme_color,
      lines: [
        `Name: ${patient.first_name} ${patient.last_name}`,
        `MRN: ${patient.patient_number}`,
        card.template.show_dob ? `DOB/Age: ${patient.date_of_birth || '-'}` : '',
        `Gender: ${patient.gender || '-'}`,
        card.template.show_phone ? `Phone: ${patient.phone || '-'}` : '',
        card.template.show_emergency_contact ? `Emergency: ${patient.emergency_contact_name || '-'} ${patient.emergency_contact_phone || ''}` : '',
        card.template.show_issue_date ? `Issue date: ${card.issue_date}${card.is_reprint ? ' (Reprint)' : ''}` : '',
        card.template.footer,
      ].filter(Boolean),
    });
  }
}
