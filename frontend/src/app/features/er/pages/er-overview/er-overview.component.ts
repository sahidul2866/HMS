import { CommonModule } from '@angular/common';
import { Component, OnDestroy, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

import { PERMISSIONS } from '../../../../core/constants/permissions';
import { User } from '../../../../core/models/auth.models';
import { DoctorDirectoryService } from '../../../../core/services/doctor-directory.service';
import { NotificationService } from '../../../../core/services/notification.service';
import { SessionService } from '../../../../core/services/session.service';
import { ERSummary, ERVisit } from '../../models/er.models';
import { ERService } from '../../services/er.service';

type BoardFilter = {
  search: string;
  acuity: string;
  status: string;
  doctor: string;
  nurse: string;
  zone: string;
  wait: string;
};

type TriageDraft = {
  temperature: string;
  pulse: string;
  bp: string;
  rr: string;
  spo2: string;
  pain: string;
  weight: string;
  consciousness: string;
  allergies: string;
  riskFlags: string[];
  observations: string;
  reason: string;
};

@Component({
  selector: 'app-er-overview',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <section class="workspace-shell er-command">
      <section class="page-card module-hero er-hero">
        <div>
          <div class="hero-kicker">Emergency Command Center</div>
          <h1 class="page-title">Live Emergency Board</h1>
          <p class="page-subtitle">Arrival, triage, assessment, treatment, observation, and disposition in one compact workflow.</p>
        </div>
        <div class="toolbar-row">
          <span class="refresh-chip">Auto refresh 30s</span>
          <button class="secondary-btn" type="button" (click)="loadOverview()">Refresh</button>
          <button class="primary-btn" type="button" *ngIf="canAny(permissions.erVisitManage, permissions.emergencyRegister)" (click)="navigateToRegister()">Quick Register</button>
        </div>
      </section>

      <section class="summary-grid" *ngIf="summary">
        <button type="button" class="summary-card" (click)="filters.status = ''"><strong>{{ summary.total_visits }}</strong><span>Total</span></button>
        <button type="button" class="summary-card" (click)="filters.status = 'waiting'"><strong>{{ summary.waiting_visits }}</strong><span>Waiting</span></button>
        <button type="button" class="summary-card" (click)="filters.status = 'triaged'"><strong>{{ summary.triaged_visits }}</strong><span>Triaged</span></button>
        <button type="button" class="summary-card" (click)="filters.status = 'assigned'"><strong>{{ summary.assigned_visits }}</strong><span>Assigned</span></button>
        <button type="button" class="summary-card" (click)="filters.status = 'in_treatment'"><strong>{{ summary.in_treatment_visits }}</strong><span>Treatment</span></button>
        <button type="button" class="summary-card" (click)="filters.status = 'admitted'"><strong>{{ summary.admitted_visits }}</strong><span>Admitted</span></button>
        <button type="button" class="summary-card" (click)="filters.status = 'discharged'"><strong>{{ summary.discharged_visits }}</strong><span>Discharged</span></button>
        <button type="button" class="summary-card" (click)="filters.status = 'referred'"><strong>{{ summary.referred_visits }}</strong><span>Referred</span></button>
      </section>

      <section class="page-card er-board-card">
        <div class="section-header">
          <div>
            <h2 class="section-title">Active Patients</h2>
            <div class="section-copy">{{ filteredVisits.length }} visible · {{ activeVisits.length }} active</div>
          </div>
          <div class="toolbar-row">
            <button class="secondary-btn" type="button" (click)="clearFilters()">Clear Filters</button>
          </div>
        </div>

        <div class="board-filters">
          <input type="search" [(ngModel)]="filters.search" placeholder="Patient, MRN, complaint, visit no" />
          <select [(ngModel)]="filters.acuity">
            <option value="">All acuity</option>
            <option value="red">Critical</option>
            <option value="orange">Emergency</option>
            <option value="yellow">Urgent</option>
            <option value="green">Semi-Urgent</option>
            <option value="blue">Non-Urgent</option>
          </select>
          <select [(ngModel)]="filters.status">
            <option value="">All status</option>
            <option *ngFor="let status of statusOptions" [value]="status">{{ statusLabel(status) }}</option>
          </select>
          <select [(ngModel)]="filters.zone">
            <option value="">All zones</option>
            <option *ngFor="let zone of zoneOptions" [value]="zone">{{ zone }}</option>
          </select>
          <select [(ngModel)]="filters.doctor">
            <option value="">All doctors</option>
            <option *ngFor="let doctor of doctors" [value]="doctor.id">{{ doctor.full_name }}</option>
          </select>
          <select [(ngModel)]="filters.nurse">
            <option value="">All nurses</option>
            <option *ngFor="let nurse of nurses" [value]="nurse.id">{{ nurse.full_name }}</option>
          </select>
          <select [(ngModel)]="filters.wait">
            <option value="">Any wait</option>
            <option value="15">15+ min</option>
            <option value="30">30+ min</option>
            <option value="60">60+ min</option>
            <option value="120">120+ min</option>
          </select>
        </div>

        <div class="board-table" *ngIf="filteredVisits.length; else emptyBoard">
          <button type="button" class="board-row" *ngFor="let visit of filteredVisits" [class.active]="selectedVisit?.id === visit.id" (click)="selectVisit(visit)">
            <span>
              <strong>{{ patientName(visit) }}</strong>
              <small>{{ visit.patient.patient_number }} · {{ visit.visit_number }}</small>
            </span>
            <span>{{ ageGender(visit) }}</span>
            <span>
              <strong>{{ visit.arrival_time | date:'shortTime' }}</strong>
              <small>{{ waitMinutes(visit) }} min wait</small>
            </span>
            <span>{{ visit.chief_complaint || 'No complaint recorded' }}</span>
            <span class="acuity-badge" [ngClass]="'acuity-' + visit.triage_category">{{ acuityLabel(visit) }}</span>
            <span class="status-badge" [ngClass]="'status-' + visit.status">{{ statusLabel(visit.status) }}</span>
            <span>{{ staffName(visit.assigned_doctor_user_id) || 'No doctor' }}</span>
            <span>{{ staffName(visit.assigned_nurse_user_id) || 'No nurse' }}</span>
            <span>{{ visit.assigned_location || 'No bed/zone' }}</span>
            <span class="alert-stack">
              <i *ngFor="let alert of alertsFor(visit)">{{ alert }}</i>
            </span>
          </button>
        </div>

        <ng-template #emptyBoard>
          <div class="table-empty">No emergency patients match the selected filters.</div>
        </ng-template>
      </section>

      <section class="er-workbench" *ngIf="selectedVisit">
        <article class="page-card patient-panel">
          <div class="section-header">
            <div>
              <h2 class="section-title">{{ patientName(selectedVisit) }}</h2>
              <div class="section-copy">{{ selectedVisit.visit_number }} · {{ selectedVisit.arrival_mode | titlecase }} · {{ selectedVisit.arrival_time | date:'short' }}</div>
            </div>
            <div class="toolbar-row">
              <button class="secondary-btn" type="button" *ngIf="canAny(permissions.erView, permissions.emergencyReportPrint)" (click)="printVisitSummary(selectedVisit)">Print Summary</button>
              <button class="secondary-btn" type="button" (click)="selectedVisit = null">Close</button>
            </div>
          </div>

          <div class="patient-snapshot">
            <span class="acuity-badge" [ngClass]="'acuity-' + selectedVisit.triage_category">{{ acuityLabel(selectedVisit) }}</span>
            <span class="status-badge" [ngClass]="'status-' + selectedVisit.status">{{ statusLabel(selectedVisit.status) }}</span>
            <span>{{ ageGender(selectedVisit) }}</span>
            <span>Zone: {{ selectedVisit.assigned_location || 'Pending' }}</span>
            <span>Doctor: {{ staffName(selectedVisit.assigned_doctor_user_id) || 'Pending' }}</span>
            <span>Nurse: {{ staffName(selectedVisit.assigned_nurse_user_id) || 'Pending' }}</span>
          </div>

          <div class="quick-actions">
            <button type="button" *ngIf="canAny(permissions.erVisitManage, permissions.emergencyStatusUpdate)" (click)="quickStatus('waiting_for_triage')">Waiting Triage</button>
            <button type="button" *ngIf="canAny(permissions.erVisitManage, permissions.emergencyStatusUpdate)" (click)="quickStatus('waiting_for_doctor')">Waiting Doctor</button>
            <button type="button" *ngIf="canAny(permissions.erVisitManage, permissions.emergencyAssess)" (click)="quickTreatmentStatus('under_assessment')">Assessing</button>
            <button type="button" *ngIf="canAny(permissions.erVisitManage, permissions.emergencyOrderCreate)" (click)="quickTreatmentStatus('orders_pending')">Orders Pending</button>
            <button type="button" *ngIf="canAny(permissions.erVisitManage, permissions.emergencyAssess)" (click)="quickTreatmentStatus('observation')">Observation</button>
            <button type="button" *ngIf="canAny(permissions.erVisitManage, permissions.emergencyDisposition)" (click)="quickTreatmentStatus('ready_for_disposition')">Ready Disposition</button>
          </div>

          <div class="tab-row">
            <button type="button" *ngFor="let tab of tabs" [class.active]="activeTab === tab.key" (click)="activeTab = tab.key">{{ tab.label }}</button>
          </div>

          <section class="tab-panel" *ngIf="activeTab === 'triage'">
            <div class="form-grid compact-grid">
              <label>Acuity
                <select [(ngModel)]="triageCategory">
                  <option value="red">Critical</option>
                  <option value="orange">Emergency</option>
                  <option value="yellow">Urgent</option>
                  <option value="green">Semi-Urgent</option>
                  <option value="blue">Non-Urgent</option>
                </select>
              </label>
              <label>Level<input type="number" min="1" max="5" [(ngModel)]="triageLevel" /></label>
              <label>Temp<input [(ngModel)]="triage.temperature" placeholder="98.6 F" /></label>
              <label>Pulse<input [(ngModel)]="triage.pulse" placeholder="/min" /></label>
              <label>BP<input [(ngModel)]="triage.bp" placeholder="120/80" /></label>
              <label>RR<input [(ngModel)]="triage.rr" placeholder="/min" /></label>
              <label>SpO2<input [(ngModel)]="triage.spo2" placeholder="%" /></label>
              <label>Pain<input type="number" min="0" max="10" [(ngModel)]="triage.pain" /></label>
              <label>Weight<input [(ngModel)]="triage.weight" /></label>
              <label>Consciousness
                <select [(ngModel)]="triage.consciousness">
                  <option>Alert</option><option>Voice responsive</option><option>Pain responsive</option><option>Unresponsive</option>
                </select>
              </label>
              <label class="wide">Allergies<input [(ngModel)]="triage.allergies" placeholder="Drug/food allergies" /></label>
              <label class="wide">Triage observations<textarea rows="2" [(ngModel)]="triage.observations"></textarea></label>
              <label class="wide">Reason for triage/re-triage<textarea rows="2" [(ngModel)]="triage.reason"></textarea></label>
            </div>
            <div class="risk-row">
              <label *ngFor="let risk of riskOptions"><input type="checkbox" [checked]="triage.riskFlags.includes(risk)" (change)="toggleRisk(risk)" /> {{ risk }}</label>
            </div>
            <button class="primary-btn" type="button" *ngIf="canAny(permissions.erTriageManage, permissions.emergencyTriage, permissions.emergencyRetriage)" (click)="saveTriage()">Save Triage</button>
          </section>

          <section class="tab-panel" *ngIf="activeTab === 'assessment'">
            <div class="template-row">
              <button type="button" *ngFor="let template of assessmentTemplates" (click)="applyTemplate(template)">{{ template.name }}</button>
            </div>
            <div class="form-grid">
              <label>Chief complaint<textarea rows="2" [(ngModel)]="assessment.chiefComplaint"></textarea></label>
              <label>History<textarea rows="3" [(ngModel)]="assessment.history"></textarea></label>
              <label>Examination<textarea rows="3" [(ngModel)]="assessment.examination"></textarea></label>
              <label>Provisional diagnosis<input [(ngModel)]="assessment.provisionalDiagnosis" /></label>
              <label>Final diagnosis<input [(ngModel)]="assessment.finalDiagnosis" /></label>
              <label class="wide">Clinical notes<textarea rows="3" [(ngModel)]="assessment.notes"></textarea></label>
              <label class="wide">Treatment plan/advice<textarea rows="3" [(ngModel)]="assessment.plan"></textarea></label>
            </div>
            <button class="primary-btn" type="button" *ngIf="canAny(permissions.erVisitManage, permissions.emergencyAssess)" (click)="saveAssessment()">Quick Save Assessment</button>
          </section>

          <section class="tab-panel" *ngIf="activeTab === 'orders'">
            <div class="template-row">
              <button type="button" *ngFor="let set of orderSets" (click)="applyOrderSet(set)">{{ set.name }}</button>
            </div>
            <div class="form-grid">
              <label>Lab/Radiology orders<textarea rows="3" [(ngModel)]="orders.investigations" placeholder="CBC, Electrolytes, ECG, X-ray chest"></textarea></label>
              <label>Medications/IV fluids<textarea rows="3" [(ngModel)]="orders.medications" placeholder="Oxygen, nebulization, IV fluids, injections"></textarea></label>
              <label>Nursing instructions<textarea rows="3" [(ngModel)]="orders.nursing"></textarea></label>
              <label>Procedures<textarea rows="3" [(ngModel)]="orders.procedures"></textarea></label>
            </div>
            <button class="primary-btn" type="button" *ngIf="canAny(permissions.erVisitManage, permissions.emergencyOrderCreate, permissions.emergencyMedicationAdminister)" (click)="saveOrders()">Save Orders/Treatment Sheet</button>
          </section>

          <section class="tab-panel" *ngIf="activeTab === 'assignment'">
            <div class="form-grid compact-grid">
              <label>Zone/Bed
                <select [(ngModel)]="assignment.location">
                  <option value="">No bed/zone</option>
                  <option *ngFor="let zone of zoneOptions" [value]="zone">{{ zone }}</option>
                </select>
              </label>
              <label>Doctor
                <select [(ngModel)]="assignment.doctorId">
                  <option value="">Unassigned</option>
                  <option *ngFor="let doctor of doctors" [value]="doctor.id">{{ doctor.full_name }}</option>
                </select>
              </label>
              <label>Nurse
                <select [(ngModel)]="assignment.nurseId">
                  <option value="">Unassigned</option>
                  <option *ngFor="let nurse of nurses" [value]="nurse.id">{{ nurse.full_name }}</option>
                </select>
              </label>
              <label class="wide">Transfer/assignment note<textarea rows="2" [(ngModel)]="assignment.note"></textarea></label>
            </div>
            <button class="primary-btn" type="button" *ngIf="canAny(permissions.erAssignmentManage, permissions.emergencyBedAssign)" (click)="saveAssignment()">Assign Bed/Team</button>
          </section>

          <section class="tab-panel" *ngIf="activeTab === 'disposition'">
            <div class="form-grid compact-grid">
              <label>Disposition
                <select [(ngModel)]="disposition.status">
                  <option value="discharged">Discharge</option>
                  <option value="admitted">Admit to IPD</option>
                  <option value="transferred">Transfer facility</option>
                  <option value="referred">Refer specialist</option>
                  <option value="observation">Observation</option>
                  <option value="death_recorded">Death record</option>
                  <option value="left_against_medical_advice">LAMA</option>
                  <option value="left_without_being_seen">Left without being seen</option>
                </select>
              </label>
              <label>Destination/referral hospital<input [(ngModel)]="disposition.facility" /></label>
              <label>Referral doctor<input [(ngModel)]="disposition.doctor" /></label>
              <label class="wide">Disposition note<textarea rows="3" [(ngModel)]="disposition.note"></textarea></label>
            </div>
            <button class="danger-btn is-destructive" type="button" *ngIf="canAny(permissions.erVisitManage, permissions.emergencyDisposition, permissions.emergencyDischarge, permissions.emergencyTransfer)" (click)="finalizeDisposition()">Finalize Disposition</button>
          </section>

          <section class="tab-panel timeline-panel" *ngIf="activeTab === 'timeline'">
            <div class="timeline-item" *ngFor="let item of timeline(selectedVisit)">
              <strong>{{ item.title }}</strong>
              <span>{{ item.time | date:'short' }}</span>
              <p>{{ item.detail }}</p>
            </div>
          </section>
        </article>
      </section>
    </section>
  `,
  styles: [
    '.er-command { display: grid; gap: 1rem; }',
    '.er-hero { display: flex; justify-content: space-between; gap: 1rem; align-items: center; }',
    '.refresh-chip { border: 1px solid var(--border); border-radius: 999px; padding: .45rem .7rem; color: var(--text-muted); font-weight: 800; }',
    '.summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: .65rem; }',
    '.summary-card { display: grid; gap: .15rem; text-align: left; border: 1px solid var(--border); border-radius: 8px; padding: .8rem; background: var(--surface); color: var(--text); }',
    '.summary-card strong { font-size: 1.35rem; }',
    '.board-filters { display: grid; grid-template-columns: 1.5fr repeat(6, minmax(120px, 1fr)); gap: .55rem; margin-bottom: .8rem; }',
    '.board-filters input, .board-filters select, .form-grid input, .form-grid select, .form-grid textarea { width: 100%; border: 1px solid var(--border); border-radius: 8px; padding: .58rem .68rem; background: var(--surface); color: var(--text); }',
    '.board-table { display: grid; gap: .4rem; }',
    '.board-row { display: grid; grid-template-columns: 1.45fr .55fr .75fr 1.3fr .72fr .9fr .95fr .95fr .9fr 1fr; gap: .55rem; align-items: center; width: 100%; border: 1px solid var(--border); border-radius: 8px; padding: .65rem; background: var(--surface); color: var(--text); text-align: left; }',
    '.board-row.active, .board-row:hover { border-color: color-mix(in srgb, var(--primary) 52%, var(--border)); background: color-mix(in srgb, var(--primary) 6%, var(--surface)); }',
    '.board-row small { display: block; color: var(--text-muted); }',
    '.acuity-badge, .status-badge { display: inline-flex; justify-content: center; border-radius: 999px; padding: .32rem .55rem; font-size: .76rem; font-weight: 900; }',
    '.acuity-red { background: #fee2e2; color: #991b1b; } .acuity-orange { background: #ffedd5; color: #9a3412; } .acuity-yellow { background: #fef9c3; color: #854d0e; } .acuity-green { background: #dcfce7; color: #166534; } .acuity-blue { background: #dbeafe; color: #1e40af; }',
    '.status-badge { background: #e2e8f0; color: #334155; } .status-discharged, .status-admitted { background: #dcfce7; color: #166534; } .status-cancelled, .status-death_recorded { background: #fee2e2; color: #991b1b; } .status-orders_pending, .status-ready_for_disposition { background: #fef3c7; color: #92400e; }',
    '.alert-stack { display: flex; flex-wrap: wrap; gap: .25rem; } .alert-stack i { border-radius: 999px; padding: .18rem .4rem; background: #fff7ed; color: #9a3412; font-style: normal; font-size: .7rem; font-weight: 900; }',
    '.er-workbench { display: grid; } .patient-panel { display: grid; gap: .8rem; }',
    '.patient-snapshot, .quick-actions, .template-row, .risk-row { display: flex; flex-wrap: wrap; gap: .45rem; align-items: center; }',
    '.patient-snapshot span:not(.acuity-badge):not(.status-badge) { border: 1px solid var(--border); border-radius: 999px; padding: .35rem .55rem; color: var(--text-muted); font-weight: 800; }',
    '.quick-actions button, .template-row button, .tab-row button, .risk-row label { border: 1px solid var(--border); border-radius: 8px; padding: .45rem .65rem; background: var(--surface); color: var(--text); font-weight: 800; }',
    '.tab-row { display: flex; gap: .35rem; overflow-x: auto; border-bottom: 1px solid var(--border); padding-bottom: .45rem; } .tab-row button.active { background: var(--primary); color: #fff; }',
    '.tab-panel { display: grid; gap: .75rem; } .form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .65rem; } .compact-grid { grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); } .wide { grid-column: 1 / -1; }',
    '.timeline-panel { gap: .45rem; } .timeline-item { border-left: 3px solid var(--primary); padding: .45rem .7rem; background: var(--surface); border-radius: 0 8px 8px 0; } .timeline-item span { color: var(--text-muted); margin-left: .5rem; } .timeline-item p { margin: .2rem 0 0; }',
    '@media (max-width: 1100px) { .board-filters, .board-row, .form-grid { grid-template-columns: 1fr; } .er-hero { align-items: stretch; flex-direction: column; } }',
  ],
})
export class EROverviewComponent implements OnDestroy {
  private readonly erService = inject(ERService);
  private readonly router = inject(Router);
  private readonly notificationService = inject(NotificationService);
  private readonly doctorDirectoryService = inject(DoctorDirectoryService);
  readonly session = inject(SessionService);
  readonly permissions = PERMISSIONS;

  summary: ERSummary | null = null;
  visits: ERVisit[] = [];
  selectedVisit: ERVisit | null = null;
  doctors: User[] = [];
  nurses: User[] = [];
  activeTab = 'triage';
  private refreshId: ReturnType<typeof setInterval> | null = null;

  filters: BoardFilter = { search: '', acuity: '', status: '', doctor: '', nurse: '', zone: '', wait: '' };
  triageCategory = 'yellow';
  triageLevel = 3;
  triage: TriageDraft = this.emptyTriage();
  assignment = { doctorId: '', nurseId: '', location: '', note: '' };
  assessment = { chiefComplaint: '', history: '', examination: '', provisionalDiagnosis: '', finalDiagnosis: '', notes: '', plan: '' };
  orders = { investigations: '', medications: '', nursing: '', procedures: '' };
  disposition = { status: 'discharged', facility: '', doctor: '', note: '' };

  readonly tabs = [
    { key: 'triage', label: 'Triage' },
    { key: 'assessment', label: 'Assessment' },
    { key: 'orders', label: 'Orders/Treatment' },
    { key: 'assignment', label: 'Bed/Team' },
    { key: 'disposition', label: 'Disposition' },
    { key: 'timeline', label: 'Timeline' },
  ];
  readonly zoneOptions = ['Triage', 'Resuscitation', 'Observation', 'Treatment', 'Minor procedure', 'Waiting'];
  readonly statusOptions = ['registered', 'waiting', 'waiting_for_triage', 'triaged', 'waiting_for_doctor', 'under_assessment', 'orders_pending', 'assigned', 'in_treatment', 'observation', 'ready_for_disposition', 'admitted', 'transferred', 'discharged', 'left_without_being_seen', 'left_against_medical_advice', 'death_recorded', 'referred', 'cancelled'];
  readonly riskOptions = ['Allergy', 'Fall risk', 'Isolation', 'Sepsis risk', 'Chest pain', 'Stroke alert', 'Pregnancy', 'Violence risk'];
  readonly assessmentTemplates = [
    { name: 'Chest Pain', diagnosis: 'Acute chest pain under evaluation', orders: 'ECG, Troponin-I, CBC, Electrolytes, Chest X-ray', plan: 'Cardiac monitoring, oxygen if hypoxic, IV access, urgent physician review.' },
    { name: 'Breathlessness', diagnosis: 'Acute respiratory distress', orders: 'SpO2 monitoring, ABG if needed, Chest X-ray, CBC', plan: 'Oxygen support, nebulization if wheeze, reassess after treatment.' },
    { name: 'Trauma', diagnosis: 'Trauma under evaluation', orders: 'CBC, X-ray/CT as indicated, blood grouping', plan: 'Primary survey, bleeding control, analgesia, immobilization as needed.' },
    { name: 'Fever', diagnosis: 'Acute febrile illness', orders: 'CBC, CRP, Blood culture if indicated, Dengue/MP as local protocol', plan: 'Antipyretic, fluids, monitor vitals and warning signs.' },
  ];
  readonly orderSets = [
    { name: 'Chest Pain', investigations: 'ECG, Troponin-I, CBC, Electrolytes, Chest X-ray', medications: 'Oxygen if SpO2 < 94%, Aspirin if not contraindicated', nursing: 'Cardiac monitor, IV line, repeat vitals every 15 minutes', procedures: '' },
    { name: 'Asthma/COPD', investigations: 'SpO2, ABG if severe, Chest X-ray', medications: 'Oxygen, Salbutamol nebulization, Ipratropium nebulization, steroid as ordered', nursing: 'Nebulization now, reassess breathing and SpO2', procedures: '' },
    { name: 'Sepsis', investigations: 'CBC, CRP, Blood culture, Lactate, RBS, Creatinine, Electrolytes', medications: 'IV fluids, antibiotics as ordered', nursing: 'Sepsis alert, strict input/output, repeat vitals', procedures: 'Two IV lines' },
  ];

  constructor() {
    this.loadOverview();
    this.doctorDirectoryService.listDoctors().subscribe((doctors) => {
      this.doctors = doctors;
      this.nurses = doctors;
    });
    this.refreshId = setInterval(() => this.loadOverview(false), 30000);
  }

  ngOnDestroy(): void {
    if (this.refreshId) clearInterval(this.refreshId);
  }

  loadOverview(showWarning = true): void {
    this.erService.getSummary().subscribe({ next: (summary) => (this.summary = summary), error: () => showWarning && this.notificationService.warning('Unable to load ER summary.') });
    this.erService.listVisits().subscribe({
      next: (visits) => {
        this.visits = visits;
        if (this.selectedVisit) {
          const refreshed = visits.find((item) => item.id === this.selectedVisit?.id) || null;
          if (refreshed) this.selectVisit(refreshed, false);
        }
      },
      error: () => showWarning && this.notificationService.warning('Unable to load ER visits.'),
    });
  }

  get activeVisits(): ERVisit[] {
    return this.visits.filter((visit) => !['discharged', 'admitted', 'transferred', 'referred', 'cancelled', 'death_recorded'].includes(visit.status));
  }

  get filteredVisits(): ERVisit[] {
    const search = this.filters.search.trim().toLowerCase();
    return this.visits
      .filter((visit) => !this.filters.acuity || visit.triage_category === this.filters.acuity)
      .filter((visit) => !this.filters.status || visit.status === this.filters.status)
      .filter((visit) => !this.filters.doctor || visit.assigned_doctor_user_id === this.filters.doctor)
      .filter((visit) => !this.filters.nurse || visit.assigned_nurse_user_id === this.filters.nurse)
      .filter((visit) => !this.filters.zone || visit.assigned_location === this.filters.zone)
      .filter((visit) => !this.filters.wait || this.waitMinutes(visit) >= Number(this.filters.wait))
      .filter((visit) => !search || [visit.visit_number, visit.patient.patient_number, this.patientName(visit), visit.chief_complaint, visit.initial_diagnosis].filter(Boolean).join(' ').toLowerCase().includes(search))
      .sort((a, b) => a.triage_level - b.triage_level || new Date(a.arrival_time).getTime() - new Date(b.arrival_time).getTime());
  }

  selectVisit(visit: ERVisit, resetTab = true): void {
    this.selectedVisit = visit;
    this.triageCategory = visit.triage_category || 'yellow';
    this.triageLevel = visit.triage_level || 3;
    this.triage = { ...this.emptyTriage(), ...this.parseVitals(visit.vitals) };
    this.assignment = { doctorId: visit.assigned_doctor_user_id || '', nurseId: visit.assigned_nurse_user_id || '', location: visit.assigned_location || '', note: '' };
    this.assessment = { ...this.assessment, chiefComplaint: visit.chief_complaint || '', provisionalDiagnosis: visit.initial_diagnosis || '' };
    this.disposition = { status: this.disposition.status, facility: visit.referral_hospital || '', doctor: visit.referral_doctor_name || '', note: visit.disposition_note || '' };
    if (resetTab) this.activeTab = 'triage';
  }

  navigateToRegister(): void {
    void this.router.navigate(['/er/register']);
  }

  clearFilters(): void {
    this.filters = { search: '', acuity: '', status: '', doctor: '', nurse: '', zone: '', wait: '' };
  }

  canAny(...permissionCodes: string[]): boolean {
    return this.session.hasAnyPermission(permissionCodes);
  }

  saveTriage(): void {
    if (!this.selectedVisit) return;
    this.erService.triageVisit(this.selectedVisit.id, {
      triage_category: this.triageCategory,
      triage_level: Number(this.triageLevel || 3),
      vitals: JSON.stringify(this.triage),
      note: this.triage.reason || this.triage.observations || null,
    }).subscribe((visit) => this.afterVisitUpdate(visit, 'Triage saved.'));
  }

  saveAssessment(): void {
    if (!this.selectedVisit) return;
    const note = this.sectionText('Doctor assessment', [
      ['Chief complaint', this.assessment.chiefComplaint],
      ['History', this.assessment.history],
      ['Examination', this.assessment.examination],
      ['Provisional Dx', this.assessment.provisionalDiagnosis],
      ['Final Dx', this.assessment.finalDiagnosis],
      ['Clinical notes', this.assessment.notes],
      ['Plan/advice', this.assessment.plan],
    ]);
    this.erService.updateTreatment(this.selectedVisit.id, {
      treatment_status: 'under_assessment',
      treatment_notes: note,
      disposition: this.selectedVisit.disposition || null,
      referral_hospital: this.selectedVisit.referral_hospital || null,
      referral_doctor_name: this.selectedVisit.referral_doctor_name || null,
      disposition_note: this.selectedVisit.disposition_note || null,
    }).subscribe((visit) => this.afterVisitUpdate(visit, 'Assessment saved.'));
  }

  saveOrders(): void {
    if (!this.selectedVisit) return;
    const note = this.sectionText('Emergency orders', [
      ['Investigations', this.orders.investigations],
      ['Medications/IV fluids', this.orders.medications],
      ['Nursing instructions', this.orders.nursing],
      ['Procedures', this.orders.procedures],
    ]);
    this.erService.updateTreatment(this.selectedVisit.id, {
      treatment_status: 'orders_pending',
      treatment_notes: note,
      disposition: this.selectedVisit.disposition || null,
      referral_hospital: this.selectedVisit.referral_hospital || null,
      referral_doctor_name: this.selectedVisit.referral_doctor_name || null,
      disposition_note: this.selectedVisit.disposition_note || null,
    }).subscribe((visit) => this.afterVisitUpdate(visit, 'Orders saved.'));
  }

  saveAssignment(): void {
    if (!this.selectedVisit) return;
    this.erService.assignVisit(this.selectedVisit.id, {
      assigned_doctor_user_id: this.assignment.doctorId || null,
      assigned_nurse_user_id: this.assignment.nurseId || null,
      assigned_location: this.assignment.location || null,
      note: this.assignment.note || null,
    }).subscribe((visit) => this.afterVisitUpdate(visit, 'Bed/team assignment saved.'));
  }

  quickStatus(status: string): void {
    if (!this.selectedVisit) return;
    this.erService.updateStatus(this.selectedVisit.id, { status, note: `Quick status update to ${this.statusLabel(status)}` }).subscribe((visit) => this.afterVisitUpdate(visit, 'Status updated.'));
  }

  quickTreatmentStatus(status: string): void {
    if (!this.selectedVisit) return;
    this.erService.updateTreatment(this.selectedVisit.id, {
      treatment_status: status,
      treatment_notes: this.selectedVisit.treatment_notes || null,
      disposition: this.selectedVisit.disposition || null,
      referral_hospital: this.selectedVisit.referral_hospital || null,
      referral_doctor_name: this.selectedVisit.referral_doctor_name || null,
      disposition_note: this.selectedVisit.disposition_note || null,
    }).subscribe((visit) => this.afterVisitUpdate(visit, 'Treatment status updated.'));
  }

  finalizeDisposition(): void {
    if (!this.selectedVisit || !window.confirm(`Finalize disposition as ${this.statusLabel(this.disposition.status)}?`)) return;
    this.erService.updateTreatment(this.selectedVisit.id, {
      treatment_status: this.disposition.status === 'observation' ? 'observation' : 'ready_for_disposition',
      treatment_notes: this.selectedVisit.treatment_notes || null,
      disposition: this.statusLabel(this.disposition.status),
      referral_hospital: this.disposition.facility || null,
      referral_doctor_name: this.disposition.doctor || null,
      disposition_note: this.disposition.note || null,
    }).subscribe(() => {
      this.erService.updateStatus(this.selectedVisit!.id, { status: this.disposition.status, note: this.disposition.note || null }).subscribe((visit) => this.afterVisitUpdate(visit, 'Disposition finalized.'));
    });
  }

  applyTemplate(template: typeof this.assessmentTemplates[number]): void {
    this.assessment.provisionalDiagnosis = template.diagnosis;
    this.assessment.plan = template.plan;
    this.orders.investigations = template.orders;
    this.activeTab = 'assessment';
  }

  applyOrderSet(set: typeof this.orderSets[number]): void {
    this.orders = { investigations: set.investigations, medications: set.medications, nursing: set.nursing, procedures: set.procedures };
  }

  toggleRisk(risk: string): void {
    this.triage.riskFlags = this.triage.riskFlags.includes(risk) ? this.triage.riskFlags.filter((item) => item !== risk) : [...this.triage.riskFlags, risk];
  }

  patientName(visit: ERVisit): string {
    return `${visit.patient.first_name} ${visit.patient.last_name}`.trim() || 'Unknown Patient';
  }

  ageGender(visit: ERVisit): string {
    return [visit.patient.date_of_birth ? this.ageFromDob(visit.patient.date_of_birth) : 'Age N/A', visit.patient.gender || 'Gender N/A'].join(' / ');
  }

  acuityLabel(visit: ERVisit): string {
    const labels: Record<string, string> = { red: 'Critical', orange: 'Emergency', yellow: 'Urgent', green: 'Semi-Urgent', blue: 'Non-Urgent' };
    return labels[visit.triage_category] || visit.triage_category;
  }

  statusLabel(status: string): string {
    return status.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());
  }

  staffName(id?: string | null): string {
    if (!id) return '';
    return [...this.doctors, ...this.nurses].find((user) => user.id === id)?.full_name || id;
  }

  waitMinutes(visit: ERVisit): number {
    return Math.max(Math.floor((Date.now() - new Date(visit.arrival_time).getTime()) / 60000), 0);
  }

  alertsFor(visit: ERVisit): string[] {
    const vitals = this.parseVitals(visit.vitals);
    const alerts: string[] = [];
    if (visit.triage_category === 'red' || visit.triage_level <= 1) alerts.push('Critical');
    if (!visit.assigned_doctor_user_id) alerts.push('No doctor');
    if (!visit.assigned_nurse_user_id) alerts.push('No nurse');
    if (this.waitMinutes(visit) > 60 && !['in_treatment', 'observation'].includes(visit.status)) alerts.push('Long wait');
    if (vitals.spo2 && Number(vitals.spo2) < 92) alerts.push('Low SpO2');
    if (vitals.pain && Number(vitals.pain) >= 7) alerts.push('Pain');
    if (vitals.allergies) alerts.push('Allergy');
    if (vitals.riskFlags?.length) alerts.push(...vitals.riskFlags.slice(0, 2));
    return Array.from(new Set(alerts)).slice(0, 4);
  }

  timeline(visit: ERVisit): Array<{ title: string; time: string; detail: string }> {
    const items = [
      { title: 'Registration', time: visit.created_at, detail: `${visit.arrival_mode} arrival. ${visit.chief_complaint || 'Chief complaint not recorded.'}` },
      { title: 'Triage', time: visit.created_at, detail: `${this.acuityLabel(visit)} level ${visit.triage_level}. ${visit.vitals || 'Vitals not recorded.'}` },
      { title: 'Assignment', time: visit.created_at, detail: `${visit.assigned_location || 'No location'} · ${this.staffName(visit.assigned_doctor_user_id) || 'No doctor'} · ${this.staffName(visit.assigned_nurse_user_id) || 'No nurse'}` },
      { title: 'Treatment/Assessment', time: visit.created_at, detail: visit.treatment_notes || 'No treatment note recorded.' },
      { title: 'Status', time: visit.discharged_at || visit.created_at, detail: this.statusLabel(visit.status) },
    ];
    if (visit.disposition) items.push({ title: 'Disposition', time: visit.discharged_at || visit.created_at, detail: [visit.disposition, visit.disposition_note].filter(Boolean).join(' - ') });
    for (const ambulance of visit.ambulance_records || []) items.push({ title: 'Ambulance Handoff', time: ambulance.received_at || ambulance.created_at, detail: `${ambulance.ambulance_service}. ${ambulance.note || ''}` });
    return items;
  }

  printVisitSummary(visit: ERVisit): void {
    const html = `<!doctype html><html><head><title>Emergency Summary ${visit.visit_number}</title><style>
      body{font-family:Arial,sans-serif;color:#111827;margin:24px;font-size:12px}.head{display:flex;justify-content:space-between;border-bottom:2px solid #111827;padding-bottom:10px}.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin:12px 0}.cell{border:1px solid #cbd5e1;padding:8px;border-radius:6px}h2{font-size:15px;margin:16px 0 8px}.badge{display:inline-block;border:1px solid #111827;border-radius:999px;padding:4px 8px;font-weight:700}pre{white-space:pre-wrap;font-family:inherit}.signature{margin-top:34px;text-align:right}</style></head><body>
      <div class="head"><div><h1>Emergency Visit Summary</h1><strong>${this.escape(visit.visit_number)}</strong></div><div>${new Date().toLocaleString()}</div></div>
      <div class="grid"><div class="cell"><b>Patient</b><br>${this.escape(this.patientName(visit))}<br>${this.escape(visit.patient.patient_number)}</div><div class="cell"><b>Arrival</b><br>${this.escape(visit.arrival_mode)} · ${new Date(visit.arrival_time).toLocaleString()}</div><div class="cell"><b>Acuity</b><br><span class="badge">${this.escape(this.acuityLabel(visit))} level ${visit.triage_level}</span></div><div class="cell"><b>Status</b><br>${this.escape(this.statusLabel(visit.status))}</div></div>
      <h2>Clinical Summary</h2><pre>${this.escape([visit.chief_complaint, visit.initial_diagnosis, visit.treatment_notes].filter(Boolean).join('\\n\\n'))}</pre>
      <h2>Vitals/Triage</h2><pre>${this.escape(visit.vitals || 'Not recorded')}</pre>
      <h2>Disposition</h2><pre>${this.escape([visit.disposition, visit.referral_hospital, visit.referral_doctor_name, visit.disposition_note].filter(Boolean).join('\\n')) || 'Pending'}</pre>
      <div class="signature">Emergency Doctor / Nurse Signature</div></body></html>`;
    const win = window.open('', '_blank', 'width=900,height=700');
    if (!win) {
      this.notificationService.warning('Unable to open print window.');
      return;
    }
    win.document.write(html);
    win.document.close();
    win.focus();
    win.print();
  }

  private afterVisitUpdate(visit: ERVisit, message: string): void {
    this.notificationService.success(message);
    this.selectedVisit = visit;
    this.visits = this.visits.map((item) => (item.id === visit.id ? visit : item));
    this.loadOverview(false);
  }

  private emptyTriage(): TriageDraft {
    return { temperature: '', pulse: '', bp: '', rr: '', spo2: '', pain: '', weight: '', consciousness: 'Alert', allergies: '', riskFlags: [], observations: '', reason: '' };
  }

  private parseVitals(value?: string | null): Partial<TriageDraft> {
    if (!value) return {};
    try {
      const parsed = JSON.parse(value);
      return typeof parsed === 'object' && parsed ? parsed : {};
    } catch {
      return { observations: value };
    }
  }

  private sectionText(title: string, rows: Array<[string, string]>): string {
    return `${title}\n${rows.filter(([, value]) => !!value).map(([label, value]) => `${label}: ${value}`).join('\n')}`;
  }

  private ageFromDob(dob: string): string {
    const birthDate = new Date(dob);
    if (Number.isNaN(birthDate.getTime())) return 'Age N/A';
    const age = new Date().getFullYear() - birthDate.getFullYear();
    return `${age}y`;
  }

  private escape(value: string): string {
    return value.replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' })[char] || char);
  }
}
