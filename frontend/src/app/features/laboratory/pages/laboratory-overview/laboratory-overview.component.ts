import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

import { SessionService } from '../../../../core/services/session.service';
import { InvestigationWorkItem, LaboratorySummary } from '../../models/laboratory.models';
import { LaboratoryServiceApi } from '../../services/laboratory.service';

@Component({
  selector: 'app-laboratory-overview',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './laboratory-overview.component.html',
  styleUrls: ['./laboratory-overview.component.scss'],
})
export class LaboratoryOverviewComponent {
  private readonly laboratoryService = inject(LaboratoryServiceApi);
  private readonly router = inject(Router);
  readonly sessionService = inject(SessionService);

  summary: LaboratorySummary | null = null;
  worklist: InvestigationWorkItem[] = [];
  queueSearch = '';

  constructor() {
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
        item.chief_complaint,
        item.diagnosis,
      ]
        .filter(Boolean)
        .some((value) => value!.toLowerCase().includes(query))
    );
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
}
