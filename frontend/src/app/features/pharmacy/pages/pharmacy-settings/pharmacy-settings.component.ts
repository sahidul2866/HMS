import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { Observable } from 'rxjs';

import { ActionConfirmationService } from '../../../../core/services/action-confirmation.service';
import { NotificationService } from '../../../../core/services/notification.service';
import { CompanyPayload, CustomerPayload, MasterPayload, PaginatedResponse } from '../../models/pharmacy.models';
import { PharmacyService } from '../../services/pharmacy.service';

type PharmacySettingKey = 'medicine-types' | 'generics' | 'companies' | 'customers';

type PharmacySettingConfig = {
  key: PharmacySettingKey;
  label: string;
  description: string;
  searchPlaceholder: string;
  fields: Array<{ key: string; label: string; type: 'text' | 'textarea' | 'email'; required?: boolean }>;
  columns: Array<{ key: string; label: string }>;
};

type MasterRow = Record<string, unknown> & { id: string; name: string };

@Component({
  selector: 'app-pharmacy-settings',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule],
  templateUrl: './pharmacy-settings.component.html',
  styleUrls: ['./pharmacy-settings.component.scss'],
})
export class PharmacySettingsComponent {
  private readonly fb = inject(FormBuilder);
  private readonly pharmacyService = inject(PharmacyService);
  private readonly notificationService = inject(NotificationService);
  private readonly confirmationService = inject(ActionConfirmationService);

  readonly configs: PharmacySettingConfig[] = [
    {
      key: 'medicine-types',
      label: 'Medicine Type Settings',
      description: 'Dosage/category groups used in the medicine catalog and filters.',
      searchPlaceholder: 'Search medicine type',
      fields: [
        { key: 'name', label: 'Name', type: 'text', required: true },
        { key: 'description', label: 'Description', type: 'textarea' },
      ],
      columns: [
        { key: 'name', label: 'Name' },
        { key: 'description', label: 'Description' },
      ],
    },
    {
      key: 'generics',
      label: 'Generic Settings',
      description: 'Generic names mapped to medicines for prescription and stock lookup.',
      searchPlaceholder: 'Search generic',
      fields: [
        { key: 'name', label: 'Name', type: 'text', required: true },
        { key: 'description', label: 'Description', type: 'textarea' },
      ],
      columns: [
        { key: 'name', label: 'Name' },
        { key: 'description', label: 'Description' },
      ],
    },
    {
      key: 'companies',
      label: 'Company Settings',
      description: 'Manufacturer and supplier contact records used by medicines and purchases.',
      searchPlaceholder: 'Search company, contact, phone',
      fields: [
        { key: 'name', label: 'Company Name', type: 'text', required: true },
        { key: 'contact_person', label: 'Contact Person', type: 'text' },
        { key: 'phone', label: 'Phone', type: 'text' },
        { key: 'email', label: 'Email', type: 'email' },
        { key: 'address', label: 'Address', type: 'textarea' },
        { key: 'note', label: 'Note', type: 'textarea' },
      ],
      columns: [
        { key: 'name', label: 'Name' },
        { key: 'contact_person', label: 'Contact' },
        { key: 'phone', label: 'Phone' },
        { key: 'email', label: 'Email' },
      ],
    },
    {
      key: 'customers',
      label: 'Customer Settings',
      description: 'Walk-in and linked patient customer records for pharmacy sales.',
      searchPlaceholder: 'Search customer name, number, phone',
      fields: [
        { key: 'name', label: 'Customer Name', type: 'text', required: true },
        { key: 'phone', label: 'Phone', type: 'text' },
        { key: 'email', label: 'Email', type: 'email' },
        { key: 'address', label: 'Address', type: 'textarea' },
        { key: 'note', label: 'Note', type: 'textarea' },
      ],
      columns: [
        { key: 'customer_number', label: 'Customer No' },
        { key: 'name', label: 'Name' },
        { key: 'phone', label: 'Phone' },
        { key: 'patient_number', label: 'Patient' },
      ],
    },
  ];

  activeConfig: PharmacySettingConfig | null = null;
  editorOpen = false;
  rows: MasterRow[] = [];
  search = '';
  page = 1;
  pageSize = 10;
  total = 0;
  editingId: string | null = null;
  saving = false;
  form = this.fb.group({});
  private searchTimer: ReturnType<typeof setTimeout> | null = null;

  get totalPages(): number {
    return Math.max(Math.ceil(this.total / this.pageSize), 1);
  }

  openEditor(config: PharmacySettingConfig): void {
    this.activeConfig = config;
    this.editorOpen = true;
    this.search = '';
    this.page = 1;
    this.editingId = null;
    this.form = this.buildForm(config);
    this.loadPage();
  }

  closeEditor(): void {
    this.editorOpen = false;
    this.activeConfig = null;
    this.rows = [];
  }

  loadPage(): void {
    if (!this.activeConfig) {
      return;
    }
    const params = { page: this.page, page_size: this.pageSize, q: this.search || undefined };
    switch (this.activeConfig.key) {
      case 'medicine-types':
        this.pharmacyService.listMedicineTypes(params).subscribe((response) => this.applyResponse(response));
        break;
      case 'generics':
        this.pharmacyService.listGenerics(params).subscribe((response) => this.applyResponse(response));
        break;
      case 'companies':
        this.pharmacyService.listCompanies(params).subscribe((response) => this.applyResponse(response));
        break;
      case 'customers':
        this.pharmacyService.listCustomers(params).subscribe((response) => this.applyResponse(response));
        break;
    }
  }

  searchNow(): void {
    this.page = 1;
    this.loadPage();
  }

  onSearchChanged(): void {
    if (this.searchTimer) {
      clearTimeout(this.searchTimer);
    }
    this.searchTimer = setTimeout(() => this.searchNow(), 300);
  }

  clearSearch(): void {
    if (this.searchTimer) {
      clearTimeout(this.searchTimer);
    }
    this.search = '';
    this.searchNow();
  }

  previousPage(): void {
    if (this.page <= 1) return;
    this.page -= 1;
    this.loadPage();
  }

  nextPage(): void {
    if (this.page >= this.totalPages) return;
    this.page += 1;
    this.loadPage();
  }

  startEdit(row: MasterRow): void {
    this.editingId = row.id;
    this.form.reset(this.extractFormValue(row));
  }

  resetForm(): void {
    this.editingId = null;
    if (this.activeConfig) {
      this.form.reset(this.emptyFormValue(this.activeConfig));
    }
  }

  submit(): void {
    if (!this.activeConfig || this.form.invalid || this.saving) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving = true;
    const label = this.activeConfig.label.replace(' Settings', '');
    switch (this.activeConfig.key) {
      case 'medicine-types':
        this.saveWith(() => {
          const payload = this.buildMasterPayload();
          return this.editingId ? this.pharmacyService.updateMedicineType(this.editingId, payload) : this.pharmacyService.createMedicineType(payload);
        }, `${label} ${this.editingId ? 'updated' : 'created'} successfully.`);
        break;
      case 'generics':
        this.saveWith(() => {
          const payload = this.buildMasterPayload();
          return this.editingId ? this.pharmacyService.updateGeneric(this.editingId, payload) : this.pharmacyService.createGeneric(payload);
        }, `${label} ${this.editingId ? 'updated' : 'created'} successfully.`);
        break;
      case 'companies':
        this.saveWith(() => {
          const payload = this.buildCompanyPayload();
          return this.editingId ? this.pharmacyService.updateCompany(this.editingId, payload) : this.pharmacyService.createCompany(payload);
        }, `${label} ${this.editingId ? 'updated' : 'created'} successfully.`);
        break;
      case 'customers':
        this.saveWith(() => {
          const payload = this.buildCustomerPayload();
          return this.editingId ? this.pharmacyService.updateCustomer(this.editingId, payload) : this.pharmacyService.createCustomer(payload);
        }, `${label} ${this.editingId ? 'updated' : 'created'} successfully.`);
        break;
    }
  }

  deleteRow(row: MasterRow): void {
    if (!this.activeConfig || !this.confirmationService.confirmDestructive(String(row.name || this.activeConfig.label))) {
      return;
    }
    const id = row.id;
    switch (this.activeConfig.key) {
      case 'medicine-types':
        this.pharmacyService.deleteMedicineType(id).subscribe(() => this.handleDelete());
        break;
      case 'generics':
        this.pharmacyService.deleteGeneric(id).subscribe(() => this.handleDelete());
        break;
      case 'companies':
        this.pharmacyService.deleteCompany(id).subscribe(() => this.handleDelete());
        break;
      case 'customers':
        this.pharmacyService.deleteCustomer(id).subscribe(() => this.handleDelete());
        break;
    }
  }

  displayCell(row: MasterRow, key: string): string {
    return String(row[key] ?? '-');
  }

  private saveWith<T>(requestFactory: () => Observable<T>, message: string): void {
    requestFactory().subscribe({
      next: () => {
        this.saving = false;
        this.notificationService.success(message);
        this.resetForm();
        this.loadPage();
      },
      error: () => {
        this.saving = false;
      },
    });
  }

  private handleDelete(): void {
    this.notificationService.success('Pharmacy setting deleted. Related selectors are refreshed.');
    this.resetForm();
    this.loadPage();
  }

  private applyResponse<T extends object>(response: PaginatedResponse<T>): void {
    this.rows = response.items as MasterRow[];
    this.total = response.total;
    this.page = response.page;
    this.pageSize = response.page_size;
  }

  private buildForm(config: PharmacySettingConfig) {
    const group: Record<string, ReturnType<FormBuilder['control']>> = {};
    for (const field of config.fields) {
      group[field.key] = this.fb.control('', field.required ? Validators.required : []);
    }
    return this.fb.group(group);
  }

  private emptyFormValue(config: PharmacySettingConfig): Record<string, string> {
    return config.fields.reduce<Record<string, string>>((acc, field) => {
      acc[field.key] = '';
      return acc;
    }, {});
  }

  private extractFormValue(row: MasterRow): Record<string, string> {
    return (this.activeConfig?.fields ?? []).reduce<Record<string, string>>((acc, field) => {
      acc[field.key] = String(row[field.key] ?? '');
      return acc;
    }, {});
  }

  private buildMasterPayload(): MasterPayload {
    const value = this.form.getRawValue() as Record<string, unknown>;
    return { name: String(value['name'] ?? '').trim(), description: this.optionalString(value['description']) };
  }

  private buildCompanyPayload(): CompanyPayload {
    const value = this.form.getRawValue() as Record<string, unknown>;
    return {
      name: String(value['name'] ?? '').trim(),
      contact_person: this.optionalString(value['contact_person']),
      phone: this.optionalString(value['phone']),
      email: this.optionalString(value['email']),
      address: this.optionalString(value['address']),
      note: this.optionalString(value['note']),
    };
  }

  private buildCustomerPayload(): CustomerPayload {
    const value = this.form.getRawValue() as Record<string, unknown>;
    return {
      name: String(value['name'] ?? '').trim(),
      phone: this.optionalString(value['phone']),
      email: this.optionalString(value['email']),
      address: this.optionalString(value['address']),
      note: this.optionalString(value['note']),
    };
  }

  private optionalString(value: unknown): string | null {
    const normalized = String(value ?? '').trim();
    return normalized ? normalized : null;
  }
}
