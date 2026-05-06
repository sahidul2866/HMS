import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';

import { NotificationService } from '../../../../core/services/notification.service';
import { SessionService } from '../../../../core/services/session.service';
import { PatientContextPanelComponent } from '../../../../shared/components/patient-context-panel/patient-context-panel.component';
import { printInvestigationStickers } from '../../../../shared/utils/investigation-sticker-printer';
import { printRadiologyReport } from '../../../../shared/utils/radiology-report-printer';
import { InvestigationWorkItem, RadiologySimulatorMachine, RadiologySummary } from '../../models/radiology.models';
import { RadiologyServiceApi } from '../../services/radiology.service';

type WorklistSortField = 'visit_date' | 'patient_name' | 'item_name' | 'status' | 'room_number';

@Component({
  selector: 'app-radiology-overview',
  standalone: true,
  imports: [CommonModule, FormsModule, PatientContextPanelComponent],
  templateUrl: './radiology-overview.component.html',
  styleUrls: ['./radiology-overview.component.scss'],
})
export class RadiologyOverviewComponent {
  private readonly radiologyService = inject(RadiologyServiceApi);
  private readonly notificationService = inject(NotificationService);
  readonly sessionService = inject(SessionService);
  private readonly sanitizer = inject(DomSanitizer);
  private readonly route = inject(ActivatedRoute);

  summary: RadiologySummary | null = null;
  worklist: InvestigationWorkItem[] = [];
  queueSearch = '';
  sortField: WorklistSortField = 'visit_date';
  sortDirection: 'asc' | 'desc' = 'desc';
  selectedItem: InvestigationWorkItem | null = null;
  reportFindings = '';
  reportImpression = '';
  reportRecommendation = '';
  staffNote = '';
  studyUid = '';
  uploadFile: File | null = null;
  viewerModalUrl: SafeResourceUrl | null = null;
  simulatorMachines: RadiologySimulatorMachine[] = [];
  selectedMachineCode = '';
  contextPatientId = '';

  constructor() {
    this.route.queryParamMap.subscribe((params) => {
      this.contextPatientId = params.get('patientId') || '';
    });
    this.loadAll();
  }

  loadAll(): void {
    this.loadSummary();
    this.loadWorklist();
    this.loadSimulatorMachines();
  }

  loadSummary(): void {
    this.radiologyService.getSummary().subscribe((summary) => (this.summary = summary));
  }

  loadWorklist(): void {
    this.radiologyService.listWorklist().subscribe((items) => (this.worklist = items));
  }

  loadSimulatorMachines(): void {
    this.radiologyService.listSimulatorMachines().subscribe((machines) => {
      this.simulatorMachines = machines;
      if (!this.selectedMachineCode && machines.length) {
        this.selectedMachineCode = machines[0].code;
      }
    });
  }

  openDetails(item: InvestigationWorkItem): void {
    if (!this.canViewStudy) {
      return;
    }
    this.selectedItem = item;
    this.reportFindings = item.result_text || '';
    this.reportImpression = '';
    this.reportRecommendation = '';
    this.staffNote = item.sample_note || '';
    this.studyUid = '';
    this.uploadFile = null;
  }

  closeDetails(): void {
    this.selectedItem = null;
  }

  closeViewerModal(): void {
    this.viewerModalUrl = null;
  }

  printSticker(item: InvestigationWorkItem): void {
    printInvestigationStickers(
      [
        {
          module: 'RADIOLOGY',
          token: item.order_id.slice(0, 8).toUpperCase(),
          patientNumber: item.patient_number,
          patientName: item.patient_name,
          invoiceNumber: this.extractInvoiceNumber(item.instructions),
          testName: item.item_name,
          roomNumber: item.room_number,
          quantity: item.quantity,
        },
      ],
      `Radiology Sticker - ${item.patient_number}`
    );
  }

  onPickFile(event: Event): void {
    const target = event.target as HTMLInputElement;
    this.uploadFile = target.files?.[0] || null;
  }

  uploadDicom(): void {
    if (!this.selectedItem || !this.uploadFile || !this.canUploadDicom) {
      return;
    }
    this.radiologyService.uploadDicom(this.selectedItem.order_id, this.uploadFile).subscribe({
      next: () => {
        this.notificationService.success('DICOM uploaded to PACS.');
        this.loadWorklist();
      },
      error: () => this.notificationService.error('Failed to upload DICOM study.'),
    });
  }

  linkStudy(): void {
    if (!this.selectedItem || !this.studyUid.trim() || !this.canUploadDicom) {
      return;
    }
    this.radiologyService
      .linkPacsStudy({
        order_id: this.selectedItem.order_id,
        study_uid: this.studyUid.trim(),
        status: 'study_uploaded',
      })
      .subscribe({
        next: () => {
          this.notificationService.success('Study linked to PACS.');
          this.loadWorklist();
        },
        error: () => this.notificationService.error('Failed to link study.'),
      });
  }

  openViewer(): void {
    if (!this.selectedItem || !this.canViewStudy) {
      return;
    }
    this.radiologyService.getViewer(this.selectedItem.order_id).subscribe({
      next: (viewer) => {
        this.viewerModalUrl = this.sanitizer.bypassSecurityTrustResourceUrl(viewer.viewer_url);
      },
      error: () => this.notificationService.warning('No uploaded study found for this order yet.'),
    });
  }

  saveReport(): void {
    if (!this.selectedItem || !this.reportFindings.trim() || !this.canAddReport) {
      return;
    }
    this.radiologyService
      .addReport({
        order_id: this.selectedItem.order_id,
        findings: this.reportFindings.trim(),
        impression: this.reportImpression.trim() || null,
        recommendation: this.reportRecommendation.trim() || null,
      })
      .subscribe({
        next: () => {
          this.notificationService.success('Radiology report saved.');
          this.loadWorklist();
        },
        error: () => this.notificationService.error('Failed to save report.'),
      });
  }

  saveStaffNote(): void {
    if (!this.selectedItem || !this.canAddReport) {
      return;
    }
    this.radiologyService
      .updateResult(this.selectedItem.order_id, {
        status: this.selectedItem.status,
        sample_note: this.staffNote.trim() || null,
        result_text: this.selectedItem.result_text || null,
      })
      .subscribe({
        next: (updated) => {
          this.selectedItem = updated;
          this.notificationService.success('Radiology note saved.');
          this.loadWorklist();
        },
        error: () => this.notificationService.error('Failed to save note.'),
      });
  }

  simulateMachineFeed(): void {
    if (!this.selectedItem || !this.selectedMachineCode || !this.canUploadDicom) {
      return;
    }
    this.radiologyService
      .simulateMachineFeed(this.selectedItem.order_id, {
        machine_code: this.selectedMachineCode,
        note: this.staffNote.trim() || null,
      })
      .subscribe({
        next: (result) => {
          this.studyUid = result.study_uid;
          this.notificationService.success(`Machine feed completed: ${result.machine_name}`);
          this.loadWorklist();
        },
        error: () => this.notificationService.error('Machine feed failed.'),
      });
  }

  markCompleted(): void {
    if (!this.selectedItem || !this.canMarkCompleted) {
      return;
    }
    this.radiologyService.markCompleted(this.selectedItem.order_id).subscribe({
      next: () => {
        this.notificationService.success('Order marked completed.');
        this.loadWorklist();
      },
      error: () => this.notificationService.error('Could not mark completed.'),
    });
  }

  get filteredWorklist(): InvestigationWorkItem[] {
    const query = this.queueSearch.trim().toLowerCase();
    return this.worklist.filter((item) =>
      (!this.contextPatientId || item.patient_id === this.contextPatientId) &&
      (!query ||
      [
        item.visit_number,
        item.patient_number,
        item.patient_name,
        item.consulting_doctor_name,
        item.item_name,
        item.room_number,
        item.chief_complaint,
        item.diagnosis,
      ]
        .filter(Boolean)
        .some((value) => value!.toLowerCase().includes(query)))
    );
  }

  get sortedWorklist(): InvestigationWorkItem[] {
    const multiplier = this.sortDirection === 'asc' ? 1 : -1;
    return [...this.filteredWorklist].sort((left, right) => {
      const leftValue = this.sortValue(left, this.sortField);
      const rightValue = this.sortValue(right, this.sortField);
      return leftValue.localeCompare(rightValue, undefined, { numeric: true, sensitivity: 'base' }) * multiplier;
    });
  }

  toggleSortDirection(): void {
    this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
  }

  statusClass(item: InvestigationWorkItem): string {
    return `work-item-card--${String(item.status || 'pending').replace(/_/g, '-')}`;
  }

  statusLabel(status: string): string {
    const labels: Record<string, string> = {
      pending_study: 'Pending Study',
      study_uploaded: 'Study Uploaded',
      ready_for_review: 'Ready for Review',
      report_completed: 'Report Completed',
      verified: 'Verified',
    };
    return labels[status] || status.replace(/_/g, ' ');
  }

  shortStudyUid(value?: string | null): string {
    if (!value) {
      return '';
    }
    return value.length > 24 ? `${value.slice(0, 24)}…` : value;
  }

  get canViewStudy(): boolean {
    return this.sessionService.hasPermission(['radiology.view']);
  }

  get canUploadDicom(): boolean {
    return this.sessionService.hasPermission(['radiology.order.create']);
  }

  get canAddReport(): boolean {
    return this.sessionService.hasPermission(['radiology.upload_image']);
  }

  get canMarkCompleted(): boolean {
    return this.sessionService.hasAnyPermission(['radiology.upload_report', 'radiology.verify_result']);
  }

  printReport(): void {
    if (!this.selectedItem || !this.canPrintReport) {
      return;
    }
    const printed = printRadiologyReport({
      orderId: this.selectedItem.order_id,
      visitNumber: this.selectedItem.visit_number,
      patientNumber: this.selectedItem.patient_number,
      patientName: this.selectedItem.patient_name,
      doctorName: this.selectedItem.consulting_doctor_name,
      studyName: this.selectedItem.item_name,
      status: this.selectedItem.status,
      findings: this.reportFindings || this.selectedItem.result_text || '',
      impression: this.reportImpression,
      recommendation: this.reportRecommendation,
      note: this.staffNote || this.selectedItem.sample_note,
      verifiedAt: this.selectedItem.verified_at,
    });
    if (!printed) {
      this.notificationService.warning('Unable to open print preview. Allow popups and try again.');
    }
  }

  get canPrintReport(): boolean {
    if (!this.selectedItem) {
      return false;
    }
    return ['report_completed', 'verified', 'completed'].includes(this.selectedItem.status) && Boolean((this.reportFindings || this.selectedItem.result_text || '').trim());
  }

  get summaryCards(): { label: string; value: number }[] {
    if (!this.summary) {
      return [];
    }
    return [
      { label: 'Pending', value: this.summary.pending_orders },
      { label: 'Ready', value: this.summary.ready_orders },
      { label: 'In Progress', value: this.summary.in_progress_orders },
      { label: 'Reported', value: this.summary.completed_orders },
      { label: 'Verified', value: this.summary.verified_orders },
    ];
  }

  get queueHealthItems(): Array<{ label: string; value: number; width: string; tone: string }> {
    const cards = this.summaryCards;
    const max = Math.max(...cards.map((item) => item.value), 1);
    return cards.map((item) => ({
      ...item,
      width: `${Math.max((item.value / max) * 100, item.value ? 10 : 0)}%`,
      tone: item.label === 'Pending' ? 'var(--accent)' : item.label === 'Verified' ? 'var(--success)' : 'var(--primary)',
    }));
  }

  private extractInvoiceNumber(instructions?: string | null): string | null {
    const match = String(instructions || '').match(/INV-\d+/);
    return match?.[0] ?? null;
  }

  private sortValue(item: InvestigationWorkItem, field: WorklistSortField): string {
    return String(item[field] || '');
  }
}
