import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { Router } from '@angular/router';

import { ERService } from '../../services/er.service';
import { ERSummary, ERVisit } from '../../models/er.models';
import { NotificationService } from '../../../../core/services/notification.service';

@Component({
  selector: 'app-er-overview',
  standalone: true,
  imports: [CommonModule],
  template: `
    <section class="er-overview">
      <header class="page-header">
        <div>
          <h1>Emergency Department</h1>
          <p>Track ER arrivals, triage, assignments, treatment progress, and disposition.</p>
        </div>
        <button class="primary" type="button" (click)="navigateToRegister()">Register ER Arrival</button>
      </header>

      <section class="summary-grid" *ngIf="summary">
        <div class="summary-card">Total: {{ summary.total_visits }}</div>
        <div class="summary-card">Waiting: {{ summary.waiting_visits }}</div>
        <div class="summary-card">Triaged: {{ summary.triaged_visits }}</div>
        <div class="summary-card">Assigned: {{ summary.assigned_visits }}</div>
        <div class="summary-card">In Treatment: {{ summary.in_treatment_visits }}</div>
        <div class="summary-card">Admitted: {{ summary.admitted_visits }}</div>
        <div class="summary-card">Discharged: {{ summary.discharged_visits }}</div>
        <div class="summary-card">Referred: {{ summary.referred_visits }}</div>
      </section>

      <section class="visit-list">
        <h2>Recent ER Visits</h2>
        <div *ngIf="!visits.length" class="empty-state">No emergency visits available yet.</div>
        <div *ngFor="let visit of visits" class="visit-card" [class.active]="selectedVisit?.id === visit.id" (click)="selectVisit(visit)">
          <div class="visit-header">
            <strong>{{ visit.visit_number }}</strong>
            <span class="status">{{ visit.status }}</span>
          </div>
          <div>{{ visit.patient.patient_number }} — {{ visit.patient.first_name }} {{ visit.patient.last_name }}</div>
          <div>{{ visit.arrival_mode | titlecase }} at {{ visit.arrival_time | date:'short' }}</div>
          <div>Complaint: {{ visit.chief_complaint || 'Not recorded' }}</div>
          <div>Triage: {{ visit.triage_category }} / level {{ visit.triage_level }}</div>
        </div>
      </section>

      <section class="visit-detail" *ngIf="selectedVisit">
        <h2>Selected Visit</h2>
        <div class="detail-grid">
          <div><strong>Patient:</strong> {{ selectedVisit.patient.first_name }} {{ selectedVisit.patient.last_name }}</div>
          <div><strong>Arrival:</strong> {{ selectedVisit.arrival_mode | titlecase }} at {{ selectedVisit.arrival_time | date:'short' }}</div>
          <div><strong>Status:</strong> {{ selectedVisit.status }}</div>
          <div><strong>Triage:</strong> {{ selectedVisit.triage_category }} / level {{ selectedVisit.triage_level }}</div>
          <div><strong>Assigned location:</strong> {{ selectedVisit.assigned_location || 'Pending' }}</div>
          <div><strong>Assigned doctor:</strong> {{ selectedVisit.assigned_doctor_user_id || 'Pending' }}</div>
          <div><strong>Disposition:</strong> {{ selectedVisit.disposition || 'Pending' }}</div>
          <div><strong>Last note:</strong> {{ selectedVisit.treatment_notes || selectedVisit.note || 'None' }}</div>
        </div>
      </section>
    </section>
  `,
  styles: [
    ".er-overview { display: grid; gap: 1rem; }",
    ".page-header { display: flex; justify-content: space-between; gap: 1rem; align-items: center; }",
    ".summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 0.75rem; }",
    ".summary-card { padding: 1rem; border: 1px solid var(--border); border-radius: 0.75rem; background: var(--surface); }",
    ".visit-list { display: grid; gap: 0.75rem; }",
    ".visit-card { padding: 1rem; border: 1px solid var(--border); border-radius: 0.75rem; cursor: pointer; background: var(--surface); }",
    ".visit-card.active { border-color: var(--primary); background: var(--surface-emphasis); }",
    ".visit-header { display: flex; justify-content: space-between; gap: 0.5rem; margin-bottom: 0.5rem; }",
    ".status { font-size: 0.9rem; color: var(--muted); }",
    ".visit-detail { padding: 1rem; border: 1px solid var(--border); border-radius: 0.75rem; background: var(--surface); }",
    ".detail-grid { display: grid; gap: 0.5rem; }",
  ],
})
export class EROverviewComponent {
  private readonly erService = inject(ERService);
  private readonly router = inject(Router);
  private readonly notificationService = inject(NotificationService);

  summary: ERSummary | null = null;
  visits: ERVisit[] = [];
  selectedVisit: ERVisit | null = null;

  constructor() {
    this.loadOverview();
  }

  loadOverview(): void {
    this.erService.getSummary().subscribe({
      next: (summary) => (this.summary = summary),
      error: () => this.notificationService.warning('Unable to load ER summary.'),
    });
    this.erService.listVisits().subscribe({
      next: (visits) => {
        this.visits = visits;
        if (this.selectedVisit) {
          this.selectedVisit = visits.find((item) => item.id === this.selectedVisit?.id) ?? null;
        }
      },
      error: () => this.notificationService.warning('Unable to load ER visits.'),
    });
  }

  selectVisit(visit: ERVisit): void {
    this.selectedVisit = visit;
  }

  navigateToRegister(): void {
    void this.router.navigate(['/er/register']);
  }
}
