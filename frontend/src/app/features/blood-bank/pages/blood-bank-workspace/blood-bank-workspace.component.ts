import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { Observable } from 'rxjs';

import { HasPermissionDirective } from '../../../../shared/directives/has-permission.directive';
import { QueueToken } from '../../../queue/models/queue.models';
import { QueueService } from '../../../queue/services/queue.service';
import { BloodBankDashboard, BloodBankReport, BloodDonor, BloodRequest, BloodUnit, StorageLocation } from '../../models/blood-bank.models';
import { BloodBankService } from '../../services/blood-bank.service';

type TabKey = 'dashboard' | 'queue' | 'donors' | 'screening' | 'collection' | 'testing' | 'components' | 'stock' | 'requests' | 'crossmatch' | 'issue' | 'transfusion' | 'return' | 'discard' | 'reports' | 'settings';

@Component({
  selector: 'app-blood-bank-workspace',
  standalone: true,
  imports: [CommonModule, FormsModule, HasPermissionDirective],
  templateUrl: './blood-bank-workspace.component.html',
  styleUrls: ['./blood-bank-workspace.component.scss'],
})
export class BloodBankWorkspaceComponent {
  private readonly bloodBank = inject(BloodBankService);
  private readonly queueService = inject(QueueService);
  private readonly route = inject(ActivatedRoute);

  readonly tabs: Array<{ key: TabKey; label: string; permission: string }> = [
    { key: 'dashboard', label: 'Dashboard', permission: 'blood_bank.dashboard.view' },
    { key: 'queue', label: 'Live Queue', permission: 'blood_bank.queue.manage' },
    { key: 'donors', label: 'Donors', permission: 'blood_bank.view' },
    { key: 'screening', label: 'Screening', permission: 'blood_bank.donor.screen' },
    { key: 'collection', label: 'Collection', permission: 'blood_bank.collection.create' },
    { key: 'testing', label: 'Testing', permission: 'blood_bank.testing.update' },
    { key: 'components', label: 'Components', permission: 'blood_bank.component.prepare' },
    { key: 'stock', label: 'Stock', permission: 'blood_bank.stock.view' },
    { key: 'requests', label: 'Requests', permission: 'blood_bank.view' },
    { key: 'crossmatch', label: 'Crossmatch', permission: 'blood_bank.crossmatch.perform' },
    { key: 'issue', label: 'Issue', permission: 'blood_bank.issue' },
    { key: 'transfusion', label: 'Transfusion', permission: 'blood_bank.transfusion.update' },
    { key: 'return', label: 'Return', permission: 'blood_bank.return' },
    { key: 'discard', label: 'Discard', permission: 'blood_bank.discard' },
    { key: 'reports', label: 'Reports', permission: 'blood_bank.report.view' },
    { key: 'settings', label: 'Settings', permission: 'blood_bank.component.prepare' },
  ];

  readonly bloodGroups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-'];
  readonly components = ['Whole Blood', 'Packed Red Blood Cells', 'Platelets', 'Fresh Frozen Plasma', 'Cryoprecipitate', 'Plasma'];
  readonly unitStatuses = ['testing_pending', 'available', 'reserved', 'crossmatched', 'issued', 'transfused', 'returned', 'discarded', 'expired', 'quarantined'];
  readonly requestStatuses = ['requested', 'sample_pending', 'sample_collected', 'crossmatch_pending', 'crossmatched', 'ready_to_issue', 'partially_issued', 'issued', 'returned', 'cancelled', 'rejected', 'discarded'];
  readonly reports = ['donor_register', 'collection', 'stock', 'blood_group_stock', 'component_stock', 'near_expiry', 'expired', 'discard', 'issue', 'transfusion', 'crossmatch', 'emergency_request', 'donor_deferral', 'reactive_screening', 'patient_usage'];

  activeTab: TabKey = 'dashboard';
  dashboard: BloodBankDashboard | null = null;
  donors: BloodDonor[] = [];
  units: BloodUnit[] = [];
  requests: BloodRequest[] = [];
  queueTokens: QueueToken[] = [];
  locations: StorageLocation[] = [];
  report: BloodBankReport | null = null;
  loading = false;
  message = '';

  filters = { q: '', blood_group: '', component_type: '', status_value: '', request_status: '', urgency: '', storage_location_id: '' };
  donorForm = { name: '', age: null as number | null, gender: '', blood_group: '', phone: '', address: '', remarks: '' };
  screeningForm = { donor_id: '', weight: null as number | null, hemoglobin_level: null as number | null, blood_pressure: '', temperature: null as number | null, pulse: null as number | null, eligibility_result: 'eligible', deferral_reason: '', next_eligible_date: '', recent_illness: '', medication_history: '', travel_history: '', remarks: '' };
  collectionForm = { donor_id: '', blood_group: '', collection_volume_ml: 450, bag_type: 'Single bag', anticoagulant_type: 'CPDA-1', collection_location: 'Blood Bank', remarks: '' };
  testForm = { unit_id: '', test_name: 'TTI Screening', test_code: 'TTI', status: 'completed', result: 'negative', result_value: '', verified: true, remarks: '' };
  componentForm = { source_unit_id: '', component_type: 'Packed Red Blood Cells', expiry_date: '', volume_ml: null as number | null, storage_location_id: '', remarks: '' };
  requestForm = { patient_id: '', blood_group: '', component_type: 'Packed Red Blood Cells', quantity_units: 1, urgency: 'routine', department_name: '', indication: '', diagnosis: '', remarks: '' };
  crossmatchForm = { request_id: '', unit_id: '', patient_blood_group: '', result: 'compatible', compatibility_status: 'compatible', emergency_override: false, override_reason: '', remarks: '' };
  issueForm = { request_id: '', unit_id: '', crossmatch_id: '', received_by: '', destination: '', transport_condition: '2-6 C maintained', emergency_override: false, override_reason: '', remarks: '' };
  transfusionForm = { issue_id: '', status: 'started', reaction_observed: false, reaction_details: '', vitals: '', remarks: '' };
  returnForm = { issue_id: '', returned_by: '', condition_on_return: 'Seal intact', minutes_outside_bank: 0, reason: '', decision: 'accept', remarks: '' };
  discardForm = { unit_id: '', reason: 'Expired', details: '' };
  locationForm = { code: '', name: '', location_type: 'refrigerator', temperature_min: 2, temperature_max: 6, current_temperature: null as number | null, remarks: '' };
  moveForm = { unit_id: '', storage_location_id: '', remarks: '' };
  reportFilters = { report_type: 'stock', date_from: '', date_to: '' };

  constructor() {
    this.route.data.subscribe((data) => {
      const tab = data['bloodBankTab'] as TabKey | undefined;
      if (tab) {
        this.activeTab = tab;
        if (tab === 'reports') this.loadReport();
      }
    });
    this.reload();
  }

  reload(): void {
    this.loading = true;
    this.bloodBank.getDashboard().subscribe((data) => (this.dashboard = data));
    this.bloodBank.listDonors({ page_size: 50, q: this.filters.q, blood_group: this.filters.blood_group }).subscribe((data) => (this.donors = data.items));
    this.bloodBank.listUnits({ page_size: 50, blood_group: this.filters.blood_group, component_type: this.filters.component_type, status_value: this.filters.status_value, storage_location_id: this.filters.storage_location_id }).subscribe((data) => {
      this.units = data.items;
      this.loading = false;
    });
    this.bloodBank.listRequests({ page_size: 50, status_value: this.filters.request_status, urgency: this.filters.urgency }).subscribe((data) => (this.requests = data.items));
    this.bloodBank.listLocations().subscribe((data) => (this.locations = data));
    this.loadQueue();
  }

  loadQueue(): void {
    this.queueService.listTokens({ queue_scope: 'blood_bank', limit: 100 }).subscribe((tokens) => (this.queueTokens = tokens));
  }

  setTab(tab: TabKey): void {
    this.activeTab = tab;
    if (tab === 'reports') this.loadReport();
  }

  activeTabLabel(): string {
    return this.tabs.find((tab) => tab.key === this.activeTab)?.label || 'Blood Bank';
  }

  createDonor(): void {
    this.run(() => this.bloodBank.createDonor(this.donorForm), 'Donor registered');
  }

  screenDonor(): void {
    this.run(() => this.bloodBank.screenDonor(this.cleanPayload(this.screeningForm)), 'Donor screening saved');
  }

  collectBlood(): void {
    this.run(() => this.bloodBank.collectBlood(this.cleanPayload(this.collectionForm)), 'Blood unit collected');
  }

  updateTest(): void {
    this.run(() => this.bloodBank.updateTest(this.cleanPayload(this.testForm)), 'Test result updated');
  }

  prepareComponent(): void {
    this.run(() => this.bloodBank.prepareComponent(this.cleanPayload(this.componentForm)), 'Component prepared');
  }

  createRequest(): void {
    this.run(() => this.bloodBank.createRequest(this.cleanPayload(this.requestForm)), 'Blood request created');
  }

  callNextBloodRequest(): void {
    this.queueService.callNext({ queue_scope: 'blood_bank' }).subscribe({
      next: () => this.reload(),
      error: (error) => (this.message = error?.error?.message || 'No blood bank request is waiting.'),
    });
  }

  updateQueueStatus(token: QueueToken, status: string): void {
    this.queueService.updateStatus(token.id, status).subscribe({
      next: () => this.reload(),
      error: (error) => (this.message = error?.error?.message || 'Unable to update blood bank queue.'),
    });
  }

  printToken(token: QueueToken): void {
    const code = `QUEUE:${token.token_number}:${token.id}`;
    const meta = token.meta || {};
    const html = `
      <html><head><title>${token.token_number}</title><style>
      body{font-family:Arial,sans-serif;margin:18px;color:#111827}.token{border:1px solid #111827;border-radius:8px;width:320px;padding:14px}
      h1{font-size:34px;margin:0 0 6px}.row{display:flex;justify-content:space-between;border-top:1px solid #e5e7eb;padding:6px 0;font-size:13px}.qr{font-family:monospace;border:1px dashed #64748b;padding:10px;margin-top:10px;word-break:break-all}
      </style></head><body><div class="token"><h1>${token.token_number}</h1>
      <div class="row"><span>Request</span><strong>${meta['request_number'] || token.source_id}</strong></div>
      <div class="row"><span>Patient</span><strong>${token.patient_label || '-'}</strong></div>
      <div class="row"><span>Blood</span><strong>${meta['blood_group'] || '-'} ${meta['component_type'] || ''}</strong></div>
      <div class="row"><span>Urgency</span><strong>${token.priority}</strong></div>
      <div class="qr">${code}</div></div><script>print(); close();</script></body></html>`;
    const win = window.open('', '_blank', 'width=420,height=520');
    if (win) {
      win.document.write(html);
      win.document.close();
    }
  }

  crossmatch(): void {
    this.run(() => this.bloodBank.crossmatch(this.cleanPayload(this.crossmatchForm)), 'Crossmatch recorded');
  }

  issue(): void {
    this.run(() => this.bloodBank.issue(this.cleanPayload(this.issueForm)), 'Blood unit issued');
  }

  updateTransfusion(): void {
    const payload = this.cleanPayload({ ...this.transfusionForm, vitals: this.parseJsonish(this.transfusionForm.vitals) });
    this.run(() => this.bloodBank.updateTransfusion(payload), 'Transfusion updated');
  }

  returnUnit(): void {
    this.run(() => this.bloodBank.returnUnit(this.cleanPayload(this.returnForm)), 'Return decision saved');
  }

  discard(): void {
    this.run(() => this.bloodBank.discard(this.cleanPayload(this.discardForm)), 'Unit discarded');
  }

  createLocation(): void {
    this.run(() => this.bloodBank.createLocation(this.cleanPayload(this.locationForm)), 'Storage location saved');
  }

  moveUnit(): void {
    this.run(() => this.bloodBank.moveUnit(this.moveForm.unit_id, this.moveForm.storage_location_id, this.moveForm.remarks), 'Unit location updated');
  }

  loadReport(): void {
    this.bloodBank.report(this.cleanPayload(this.reportFilters)).subscribe((data) => (this.report = data));
  }

  statusTone(status: string | null | undefined): string {
    const value = String(status || '').toLowerCase();
    if (['available', 'eligible', 'completed', 'compatible', 'issued'].includes(value)) return 'good';
    if (['expired', 'discarded', 'quarantined', 'reactive', 'positive', 'incompatible', 'rejected'].includes(value)) return 'danger';
    if (['emergency', 'testing_pending', 'pending', 'crossmatch_pending', 'sample_required', 'reserved'].includes(value)) return 'warning';
    return 'neutral';
  }

  safeUnit(unit: BloodUnit): boolean {
    return unit.testing_status === 'completed' && ['available', 'crossmatched', 'reserved'].includes(unit.status);
  }

  queueTone(token: QueueToken): string {
    if (token.priority === 'emergency' || token.status === 'rejected' || token.status === 'discarded') return 'danger';
    if (token.priority === 'urgent' || ['requested', 'sample_pending', 'crossmatch_pending', 'ready_to_issue'].includes(token.status)) return 'warning';
    if (['crossmatched', 'issued', 'returned'].includes(token.status)) return 'good';
    return 'neutral';
  }

  queueMeta(token: QueueToken, key: string): string {
    const value = token.meta?.[key];
    return value === undefined || value === null || value === '' ? '-' : String(value);
  }

  private run(factory: () => Observable<unknown>, success: string): void {
    this.loading = true;
    this.message = '';
    factory().subscribe({
      next: () => {
        this.message = success;
        this.reload();
      },
      error: (error: any) => {
        this.loading = false;
        this.message = error?.error?.message || 'Action failed';
      },
    });
  }

  private cleanPayload<T extends Record<string, unknown>>(payload: T): T {
    return Object.fromEntries(Object.entries(payload).filter(([, value]) => value !== '' && value !== null && value !== undefined)) as T;
  }

  private parseJsonish(value: string): Record<string, unknown> | undefined {
    if (!value.trim()) return undefined;
    try {
      return JSON.parse(value);
    } catch {
      return { note: value };
    }
  }
}
