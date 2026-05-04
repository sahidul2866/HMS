import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule, ReactiveFormsModule, FormBuilder, Validators } from '@angular/forms';

import { NotificationService } from '../../../../core/services/notification.service';
import { InvestigationSettingPayload, PharmacyInvestigationSetting } from '../../../pharmacy/models/pharmacy.models';
import { PharmacyService } from '../../../pharmacy/services/pharmacy.service';

@Component({
  selector: 'app-diagnostics-settings',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule],
  templateUrl: './pharmacy-investigation-settings.component.html',
  styleUrls: ['./pharmacy-investigation-settings.component.scss'],
})
export class PharmacyInvestigationSettingsComponent {
  private readonly fb = inject(FormBuilder);
  private readonly pharmacyService = inject(PharmacyService);
  private readonly notificationService = inject(NotificationService);

  settings: PharmacyInvestigationSetting[] = [];
  search = '';
  serviceAreaFilter = '';
  activeFilter = 'true';
  page = 1;
  pageSize = 10;
  total = 0;
  editingId: string | null = null;
  editorOpen = false;
  sortField: 'code' | 'test_name' | 'category' | 'service_area' | 'fee' | 'status' = 'test_name';
  sortDirection: 'asc' | 'desc' = 'asc';
  private searchDebounceTimer: ReturnType<typeof setTimeout> | null = null;

  readonly form = this.fb.group({
    category_name: ['', Validators.required],
    test_name: ['', Validators.required],
    code: ['', Validators.required],
    service_area: ['laboratory', Validators.required],
    fee: [0, [Validators.required, Validators.min(0)]],
    room_number: [''],
    normal_range: [''],
    unit: [''],
    description: [''],
    specimen_type: [''],
    turnaround_time: [''],
    report_header: [''],
    report_template: [''],
    report_note_template: [''],
    requires_report: [true],
    is_active: [true],
  });

  constructor() {
    this.loadPage();
  }

  get activeCount(): number {
    return this.settings.filter((item) => item.is_active).length;
  }

  get inactiveCount(): number {
    return this.settings.filter((item) => !item.is_active).length;
  }

  get totalPages(): number {
    return Math.max(Math.ceil(this.total / this.pageSize), 1);
  }

  loadPage(): void {
    this.pharmacyService
      .listInvestigationSettings({
        page: this.page,
        page_size: this.pageSize,
        q: this.search || undefined,
        service_area: this.serviceAreaFilter || undefined,
        is_active: this.activeFilter === '' ? undefined : this.activeFilter,
      })
      .subscribe((response) => {
        this.settings = response.items;
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

  toggleSort(field: PharmacyInvestigationSettingsComponent['sortField']): void {
    if (this.sortField === field) {
      this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
      return;
    }
    this.sortField = field;
    this.sortDirection = 'asc';
  }

  get displayedSettings(): PharmacyInvestigationSetting[] {
    const dir = this.sortDirection === 'asc' ? 1 : -1;
    return [...this.settings].sort((a, b) => {
      switch (this.sortField) {
        case 'code':
          return dir * (a.code || '').localeCompare(b.code || '');
        case 'category':
          return dir * (a.category_name || '').localeCompare(b.category_name || '');
        case 'service_area':
          return dir * (a.service_area || '').localeCompare(b.service_area || '');
        case 'fee':
          return dir * (Number(a.fee || 0) - Number(b.fee || 0));
        case 'status':
          return dir * Number(a.is_active) - dir * Number(b.is_active);
        case 'test_name':
        default:
          return dir * (a.test_name || '').localeCompare(b.test_name || '');
      }
    });
  }

  openCreate(): void {
    this.resetForm();
    this.editorOpen = true;
  }

  edit(item: PharmacyInvestigationSetting): void {
    this.editingId = item.id;
    this.form.reset({
      category_name: item.category_name,
      test_name: item.test_name,
      code: item.code,
      service_area: item.service_area,
      fee: Number(item.fee),
      room_number: item.room_number || '',
      normal_range: item.normal_range || '',
      unit: item.unit || '',
      description: item.description || '',
      specimen_type: item.specimen_type || '',
      turnaround_time: item.turnaround_time || '',
      report_header: item.report_header || '',
      report_template: item.report_template || '',
      report_note_template: item.report_note_template || '',
      requires_report: item.requires_report,
      is_active: item.is_active,
    });
    this.editorOpen = true;
  }

  closeEditor(): void {
    this.editorOpen = false;
    this.resetForm();
  }

  resetForm(): void {
    this.editingId = null;
    this.form.reset({
      category_name: '',
      test_name: '',
      code: '',
      service_area: 'laboratory',
      fee: 0,
      room_number: '',
      normal_range: '',
      unit: '',
      description: '',
      specimen_type: '',
      turnaround_time: '',
      report_header: '',
      report_template: '',
      report_note_template: '',
      requires_report: true,
      is_active: true,
    });
  }

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const raw = this.form.getRawValue();
    const payload: InvestigationSettingPayload = {
      category_name: raw.category_name || '',
      test_name: raw.test_name || '',
      code: raw.code || '',
      service_area: raw.service_area || 'laboratory',
      fee: Number(raw.fee || 0),
      room_number: raw.room_number || null,
      normal_range: raw.normal_range || null,
      unit: raw.unit || null,
      description: raw.description || null,
      specimen_type: raw.specimen_type || null,
      turnaround_time: raw.turnaround_time || null,
      report_header: raw.report_header || null,
      report_template: raw.report_template || null,
      report_note_template: raw.report_note_template || null,
      requires_report: !!raw.requires_report,
      is_active: !!raw.is_active,
    };
    const request = this.editingId
      ? this.pharmacyService.updateInvestigationSetting(this.editingId, payload)
      : this.pharmacyService.createInvestigationSetting(payload);
    request.subscribe(() => {
      this.notificationService.success(`Investigation setting ${this.editingId ? 'updated' : 'created'} successfully.`);
      this.closeEditor();
      this.loadPage();
    });
  }

  remove(item: PharmacyInvestigationSetting): void {
    if (!window.confirm(`Delete ${item.test_name}?`)) {
      return;
    }
    this.pharmacyService.deleteInvestigationSetting(item.id).subscribe(() => {
      this.notificationService.success('Investigation setting deleted successfully.');
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
}
