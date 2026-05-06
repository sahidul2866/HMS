import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { SessionService } from '../../../../core/services/session.service';
import { PatientContextPanelComponent } from '../../../../shared/components/patient-context-panel/patient-context-panel.component';
import { printInvestigationStickers } from '../../../../shared/utils/investigation-sticker-printer';
import { InvestigationWorkItem, LaboratorySummary } from '../../models/laboratory.models';
import { LaboratoryServiceApi } from '../../services/laboratory.service';

type WorklistSortField = 'visit_date' | 'patient_name' | 'item_name' | 'status' | 'room_number';

@Component({
  selector: 'app-laboratory-overview',
  standalone: true,
  imports: [CommonModule, FormsModule, PatientContextPanelComponent],
  templateUrl: './laboratory-overview.component.html',
  styleUrls: ['./laboratory-overview.component.scss'],
})
export class LaboratoryOverviewComponent {
  private readonly laboratoryService = inject(LaboratoryServiceApi);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  readonly sessionService = inject(SessionService);

  summary: LaboratorySummary | null = null;
  worklist: InvestigationWorkItem[] = [];
  queueSearch = '';
  sortField: WorklistSortField = 'visit_date';
  sortDirection: 'asc' | 'desc' = 'desc';
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
  }

  loadSummary(): void {
    this.laboratoryService.getSummary().subscribe((summary) => (this.summary = summary));
  }

  loadWorklist(): void {
    this.laboratoryService.listWorklist().subscribe((items) => (this.worklist = items));
  }

  openWorkbench(item: InvestigationWorkItem): void {
    void this.router.navigate(['/laboratory/workbench', item.order_id]);
  }

  printSticker(item: InvestigationWorkItem): void {
    printInvestigationStickers(
      [
        {
          module: 'LABORATORY',
          token: item.order_id.slice(0, 8).toUpperCase(),
          patientNumber: item.patient_number,
          patientName: item.patient_name,
          invoiceNumber: this.extractInvoiceNumber(item.instructions),
          testName: item.item_name,
          roomNumber: item.room_number,
          quantity: item.quantity,
        },
      ],
      `Lab Sticker - ${item.patient_number}`
    );
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

  get summaryCards(): { label: string; value: number }[] {
    if (!this.summary) {
      return [];
    }
    return [
      { label: 'Pending', value: this.summary.pending_orders },
      { label: 'Collected', value: this.summary.collected_orders },
      { label: 'In Progress', value: this.summary.in_progress_orders },
      { label: 'Completed', value: this.summary.completed_orders },
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
