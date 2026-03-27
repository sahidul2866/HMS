import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

import { SessionService } from '../../../../core/services/session.service';
import { InvestigationWorkItem, RadiologySummary } from '../../models/radiology.models';
import { RadiologyServiceApi } from '../../services/radiology.service';

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
      { label: 'Ready', value: this.summary.ready_orders },
      { label: 'In Progress', value: this.summary.in_progress_orders },
      { label: 'Reported', value: this.summary.completed_orders },
      { label: 'Verified', value: this.summary.verified_orders },
    ];
  }
}
