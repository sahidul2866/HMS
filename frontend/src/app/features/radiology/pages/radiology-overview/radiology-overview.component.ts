import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

import { SessionService } from '../../../../core/services/session.service';
import { printInvestigationStickers } from '../../../../shared/utils/investigation-sticker-printer';
import { InvestigationWorkItem, RadiologySummary } from '../../models/radiology.models';
import { RadiologyServiceApi } from '../../services/radiology.service';

type WorklistSortField = 'visit_date' | 'patient_name' | 'item_name' | 'status' | 'room_number';

@Component({
  selector: 'app-radiology-overview',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './radiology-overview.component.html',
  styleUrls: ['./radiology-overview.component.scss'],
})
export class RadiologyOverviewComponent {
  private readonly radiologyService = inject(RadiologyServiceApi);
  private readonly router = inject(Router);
  readonly sessionService = inject(SessionService);

  summary: RadiologySummary | null = null;
  worklist: InvestigationWorkItem[] = [];
  queueSearch = '';
  sortField: WorklistSortField = 'visit_date';
  sortDirection: 'asc' | 'desc' = 'desc';

  constructor() {
    this.loadAll();
  }

  loadAll(): void {
    this.loadSummary();
    this.loadWorklist();
  }

  loadSummary(): void {
    this.radiologyService.getSummary().subscribe((summary) => (this.summary = summary));
  }

  loadWorklist(): void {
    this.radiologyService.listWorklist().subscribe((items) => (this.worklist = items));
  }

  openWorkbench(item: InvestigationWorkItem): void {
    void this.router.navigate(['/radiology/workbench', item.order_id]);
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

  get filteredWorklist(): InvestigationWorkItem[] {
    const query = this.queueSearch.trim().toLowerCase();
    if (!query) {
      return this.worklist;
    }
    return this.worklist.filter((item) =>
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
        .some((value) => value!.toLowerCase().includes(query))
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
      { label: 'Ready', value: this.summary.ready_orders },
      { label: 'In Progress', value: this.summary.in_progress_orders },
      { label: 'Reported', value: this.summary.completed_orders },
      { label: 'Verified', value: this.summary.verified_orders },
    ];
  }

  private extractInvoiceNumber(instructions?: string | null): string | null {
    const match = String(instructions || '').match(/INV-\d+/);
    return match?.[0] ?? null;
  }

  private sortValue(item: InvestigationWorkItem, field: WorklistSortField): string {
    return String(item[field] || '');
  }
}
