import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormArray, FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { ActionConfirmationService } from '../../../../core/services/action-confirmation.service';
import { NotificationService } from '../../../../core/services/notification.service';
import { Patient } from '../../../patients/models/patient.models';
import { PatientService } from '../../../patients/services/patient.service';
import { InvestigationPayload, PharmacyCustomer, PharmacyInvestigation, PharmacyInvestigationSetting } from '../../../pharmacy/models/pharmacy.models';
import { PharmacyService } from '../../../pharmacy/services/pharmacy.service';

@Component({
  selector: 'app-diagnostics-orders',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule],
  templateUrl: './pharmacy-investigations.component.html',
  styleUrls: ['./pharmacy-investigations.component.scss'],
})
export class PharmacyInvestigationsComponent {
  private readonly fb = inject(FormBuilder);
  private readonly pharmacyService = inject(PharmacyService);
  private readonly patientService = inject(PatientService);
  private readonly notificationService = inject(NotificationService);
  private readonly confirmationService = inject(ActionConfirmationService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  investigations: PharmacyInvestigation[] = [];
  settings: PharmacyInvestigationSetting[] = [];
  customers: PharmacyCustomer[] = [];
  patients: Patient[] = [];
  selectedInvestigation: PharmacyInvestigation | null = null;
  draftMessage = '';
  editorOpen = false;

  search = '';
  statusFilter = '';
  serviceAreaFilter = '';
  customerFilter = '';
  dateFrom = '';
  dateTo = '';
  page = 1;
  pageSize = 10;
  total = 0;
  sortField: 'number' | 'tests' | 'customer' | 'status' | 'total_amount' | 'ordered_at' = 'ordered_at';
  sortDirection: 'asc' | 'desc' = 'desc';
  private searchDebounceTimer: ReturnType<typeof setTimeout> | null = null;

  readonly form = this.fb.group({
    customer_id: [''],
    patient_id: [''],
    source_visit_id: [''],
    ordered_at: [new Date().toISOString().slice(0, 10), Validators.required],
    status: ['ordered', Validators.required],
    discount_amount: [0, [Validators.required, Validators.min(0)]],
    report_note: [''],
    note: [''],
    report_title: [''],
    report_footer_note: [''],
    printable_schema: [''],
    items: this.fb.array([]),
  });

  constructor() {
    this.loadReferenceData();
    this.loadPage();
    this.addItem();
    this.route.queryParamMap.subscribe((params) => {
      const opdVisitId = params.get('opdVisitId');
      if (opdVisitId) {
        this.loadDraft(opdVisitId);
      }
    });
  }

  get selectedItemCount(): number {
    return this.items.length;
  }

  get totalPages(): number {
    return Math.max(Math.ceil(this.total / this.pageSize), 1);
  }

  get items(): FormArray {
    return this.form.controls.items as FormArray;
  }

  loadReferenceData(): void {
    this.pharmacyService.listInvestigationSettings({ page: 1, page_size: 100, is_active: 'true' }).subscribe((response) => (this.settings = response.items));
    this.pharmacyService.listCustomers({ page: 1, page_size: 100 }).subscribe((response) => (this.customers = response.items));
    this.patientService.list().subscribe((patients) => (this.patients = patients));
  }

  loadPage(): void {
    this.pharmacyService
      .listInvestigations({
        page: this.page,
        page_size: this.pageSize,
        q: this.search || undefined,
        status: this.statusFilter || undefined,
        service_area: this.serviceAreaFilter || undefined,
        customer_id: this.customerFilter || undefined,
        date_from: this.dateFrom || undefined,
        date_to: this.dateTo || undefined,
      })
      .subscribe((response) => {
        this.investigations = response.items;
        this.total = response.total;
        this.page = response.page;
      });
  }

  searchNow(): void {
    this.page = 1;
    this.loadPage();
  }

  onFiltersChanged(): void {
    this.page = 1;
    if (this.searchDebounceTimer) clearTimeout(this.searchDebounceTimer);
    this.searchDebounceTimer = setTimeout(() => this.loadPage(), 250);
  }

  toggleSort(field: PharmacyInvestigationsComponent['sortField']): void {
    if (this.sortField === field) {
      this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
      return;
    }
    this.sortField = field;
    this.sortDirection = field === 'ordered_at' ? 'desc' : 'asc';
  }

  get displayedInvestigations(): PharmacyInvestigation[] {
    const dir = this.sortDirection === 'asc' ? 1 : -1;
    return [...this.investigations].sort((a, b) => {
      switch (this.sortField) {
        case 'number':
          return dir * (a.investigation_number || '').localeCompare(b.investigation_number || '');
        case 'tests':
          return dir * (Number(a.test_count || 0) - Number(b.test_count || 0));
        case 'customer':
          return dir * this.patientOrCustomerLabel(a).localeCompare(this.patientOrCustomerLabel(b));
        case 'status':
          return dir * (a.status || '').localeCompare(b.status || '');
        case 'total_amount':
          return dir * (Number(a.total_amount || 0) - Number(b.total_amount || 0));
        case 'ordered_at':
        default:
          return dir * (a.ordered_at || '').localeCompare(b.ordered_at || '');
      }
    });
  }

  openCreate(): void {
    this.resetForm(false);
    this.editorOpen = true;
  }

  selectInvestigation(item: PharmacyInvestigation): void {
    this.selectedInvestigation = item;
    this.items.clear();
    for (const testItem of item.items) {
        this.items.push(
        this.fb.group({
          setting_id: [testItem.setting_id, Validators.required],
          source_visit_order_id: [testItem.source_visit_order_id || ''],
          status: [testItem.status, Validators.required],
          fee: [Number(testItem.fee), [Validators.required, Validators.min(0)]],
          result_text: [testItem.result_text || ''],
          note: [testItem.note || ''],
        }),
      );
    }
    this.form.patchValue({
      customer_id: item.customer_id || '',
      patient_id: item.patient_id || '',
      source_visit_id: item.source_visit_id || '',
      ordered_at: item.ordered_at,
      status: item.status,
      discount_amount: Number(item.discount_amount),
      report_note: item.report_note || '',
      note: item.note || '',
      report_title: item.report_title || '',
      report_footer_note: item.report_footer_note || '',
      printable_schema: item.printable_schema || '',
    });
    this.editorOpen = true;
  }

  closeEditor(): void {
    this.editorOpen = false;
    this.resetForm();
  }

  resetForm(clearRoute = true): void {
    this.selectedInvestigation = null;
    this.draftMessage = '';
    this.items.clear();
    this.addItem();
    this.form.reset({
      customer_id: '',
      patient_id: '',
      source_visit_id: '',
      ordered_at: new Date().toISOString().slice(0, 10),
      status: 'ordered',
      discount_amount: 0,
      report_note: '',
      note: '',
      report_title: '',
      report_footer_note: '',
      printable_schema: '',
    });
    if (clearRoute) {
      void this.router.navigate([], { relativeTo: this.route, queryParams: { opdVisitId: null }, queryParamsHandling: 'merge' });
    }
  }

  addItem(): void {
    this.items.push(
      this.fb.group({
        setting_id: ['', Validators.required],
        source_visit_order_id: [''],
        status: ['ordered', Validators.required],
        fee: [0, [Validators.required, Validators.min(0)]],
        result_text: [''],
        note: [''],
      }),
    );
  }

  removeItem(index: number): void {
    if (this.items.length === 1) {
      return;
    }
    this.items.removeAt(index);
  }

  onSettingChanged(index: number): void {
    const settingId = this.items.at(index).get('setting_id')?.value;
    const setting = this.settings.find((item) => item.id === settingId);
    if (!setting) {
      return;
    }
    this.items.at(index).patchValue({ fee: Number(setting.fee) });
    if (!this.form.get('report_title')?.value) {
      this.form.patchValue({ report_title: `Investigation Report - ${setting.category_name}` });
    }
  }

  get subtotal(): number {
    return this.items.controls.reduce((sum, control) => sum + Number(control.get('fee')?.value || 0), 0);
  }

  get netTotal(): number {
    return Math.max(this.subtotal - Number(this.form.get('discount_amount')?.value || 0), 0);
  }

  patientOrCustomerLabel(item: PharmacyInvestigation): string {
    return item.customer_name || item.patient_name || '-';
  }

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const raw = this.form.getRawValue();
    const payload: InvestigationPayload = {
      customer_id: raw.customer_id || null,
      patient_id: raw.patient_id || null,
      source_visit_id: raw.source_visit_id || null,
      ordered_at: raw.ordered_at || new Date().toISOString().slice(0, 10),
      status: raw.status || 'ordered',
      discount_amount: Number(raw.discount_amount || 0),
      report_note: raw.report_note || null,
      note: raw.note || null,
      report_title: raw.report_title || null,
      report_footer_note: raw.report_footer_note || null,
      printable_schema: raw.printable_schema || null,
      items: ((raw.items || []) as Array<Record<string, unknown>>).map((item) => ({
        setting_id: String(item['setting_id'] || ''),
        source_visit_order_id: String(item['source_visit_order_id'] || '') || null,
        status: String(item['status'] || 'ordered'),
        fee: Number(item['fee'] || 0),
        result_text: String(item['result_text'] || '') || null,
        note: String(item['note'] || '') || null,
      })),
    };
    const request = this.selectedInvestigation
      ? this.pharmacyService.updateInvestigation(this.selectedInvestigation.id, payload)
      : this.pharmacyService.createInvestigation(payload);
    request.subscribe((item) => {
      this.notificationService.success(`Investigation ${this.selectedInvestigation ? 'updated' : 'created'}. Worklist and billing context are refreshed.`);
      this.selectedInvestigation = item;
      this.selectInvestigation(item);
      this.draftMessage = '';
      this.editorOpen = false;
      void this.router.navigate([], { relativeTo: this.route, queryParams: { opdVisitId: null }, queryParamsHandling: 'merge' });
      this.loadPage();
    });
  }

  remove(item: PharmacyInvestigation): void {
    if (!this.confirmationService.confirmDestructive(item.investigation_number)) {
      return;
    }
    this.pharmacyService.deleteInvestigation(item.id).subscribe(() => {
      this.notificationService.success(`Investigation ${item.investigation_number} deleted.`);
      this.selectedInvestigation = this.selectedInvestigation?.id === item.id ? null : this.selectedInvestigation;
      this.loadPage();
    });
  }

  previousPage(): void {
    if (this.page <= 1) {
      return;
    }
    this.page -= 1;
    this.loadPage();
  }

  nextPage(): void {
    if (this.page >= this.totalPages) {
      return;
    }
    this.page += 1;
    this.loadPage();
  }

  private loadDraft(visitId: string): void {
    this.pharmacyService.getInvestigationDraftFromVisit(visitId).subscribe({
      next: (draft) => {
        this.selectedInvestigation = null;
        this.items.clear();
        for (const item of draft.items) {
          this.items.push(
            this.fb.group({
              setting_id: [item.setting_id || '', Validators.required],
              source_visit_order_id: [item.source_visit_order_id],
              status: ['ordered', Validators.required],
              fee: [Number(item.fee || 0), [Validators.required, Validators.min(0)]],
              result_text: [''],
              note: [item.instruction || item.warning || ''],
            }),
          );
        }
        this.form.patchValue({
          customer_id: draft.customer_id || '',
          patient_id: draft.patient_id,
          source_visit_id: draft.source_visit_id,
          ordered_at: new Date().toISOString().slice(0, 10),
          status: 'ordered',
          discount_amount: 0,
          report_title: draft.report_title || '',
          note: draft.note || '',
        });
        this.draftMessage = draft.message || 'Investigation draft loaded.';
        this.editorOpen = true;
      },
      error: () => {
        this.notificationService.warning('Investigation draft is no longer available for this OPD visit.');
        this.draftMessage = '';
        void this.router.navigate([], { relativeTo: this.route, queryParams: { opdVisitId: null }, queryParamsHandling: 'merge' });
      },
    });
  }
}
