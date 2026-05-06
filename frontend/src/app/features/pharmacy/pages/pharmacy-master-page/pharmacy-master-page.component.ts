import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { Observable } from 'rxjs';
import { ActivatedRoute } from '@angular/router';

import { ActionConfirmationService } from '../../../../core/services/action-confirmation.service';
import { NotificationService } from '../../../../core/services/notification.service';
import {
  CompanyPayload,
  CustomerPayload,
  MasterPayload,
  PaginatedResponse,
} from '../../models/pharmacy.models';
import { PharmacyService } from '../../services/pharmacy.service';

type EntityKey = 'medicine-types' | 'generics' | 'companies' | 'customers';

type MasterField = {
  key: string;
  label: string;
  type: 'text' | 'textarea' | 'email';
  required?: boolean;
};

type MasterPageConfig = {
  entityKey: EntityKey;
  title: string;
  subtitle: string;
  eyebrow: string;
  createLabel: string;
  searchPlaceholder: string;
  fields: MasterField[];
  columns: Array<{ key: string; label: string }>;
};

type MasterRow = Record<string, unknown> & {
  id: string;
  name: string;
};

@Component({
  selector: 'app-pharmacy-master-page',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule],
  templateUrl: './pharmacy-master-page.component.html',
  styleUrls: ['./pharmacy-master-page.component.scss'],
})
export class PharmacyMasterPageComponent {
  private readonly fb = inject(FormBuilder);
  private readonly route = inject(ActivatedRoute);
  private readonly pharmacyService = inject(PharmacyService);
  private readonly notificationService = inject(NotificationService);
  private readonly confirmationService = inject(ActionConfirmationService);

  readonly config = this.route.snapshot.data['config'] as MasterPageConfig;
  readonly form = this.buildForm();

  rows: MasterRow[] = [];
  search = '';
  page = 1;
  pageSize = 10;
  total = 0;
  editingId: string | null = null;
  saving = false;
  private searchTimer: ReturnType<typeof setTimeout> | null = null;

  constructor() {
    this.loadPage();
  }

  get totalPages(): number {
    return Math.max(Math.ceil(this.total / this.pageSize), 1);
  }

  loadPage(): void {
    const params = { page: this.page, page_size: this.pageSize, q: this.search || undefined };
    switch (this.config.entityKey) {
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

  startEdit(row: MasterRow): void {
    this.editingId = String(row['id']);
    this.form.reset(this.extractFormValue(row));
  }

  resetForm(): void {
    this.editingId = null;
    this.form.reset(this.emptyFormValue());
  }

  submit(): void {
    if (this.form.invalid || this.saving) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving = true;
    switch (this.config.entityKey) {
      case 'medicine-types':
        this.saveWith(
          () => {
            const payload = this.buildMasterPayload();
            return this.editingId ? this.pharmacyService.updateMedicineType(this.editingId, payload) : this.pharmacyService.createMedicineType(payload);
          },
          `Medicine type ${this.editingId ? 'updated' : 'created'} successfully.`,
        );
        break;
      case 'generics':
        this.saveWith(
          () => {
            const payload = this.buildMasterPayload();
            return this.editingId ? this.pharmacyService.updateGeneric(this.editingId, payload) : this.pharmacyService.createGeneric(payload);
          },
          `Generic information ${this.editingId ? 'updated' : 'created'} successfully.`,
        );
        break;
      case 'companies':
        this.saveWith(
          () => {
            const payload = this.buildCompanyPayload();
            return this.editingId ? this.pharmacyService.updateCompany(this.editingId, payload) : this.pharmacyService.createCompany(payload);
          },
          `Medicine company ${this.editingId ? 'updated' : 'created'} successfully.`,
        );
        break;
      case 'customers':
        this.saveWith(
          () => {
            const payload = this.buildCustomerPayload();
            return this.editingId ? this.pharmacyService.updateCustomer(this.editingId, payload) : this.pharmacyService.createCustomer(payload);
          },
          `Customer information ${this.editingId ? 'updated' : 'created'} successfully.`,
        );
        break;
    }
  }

  deleteRow(row: MasterRow): void {
    const id = String(row['id']);
    const name = row['name'] || this.config.title;
    if (!this.confirmationService.confirmDestructive(String(name))) {
      return;
    }
    switch (this.config.entityKey) {
      case 'medicine-types':
        this.pharmacyService.deleteMedicineType(id).subscribe(() => this.handleDelete('Medicine type deleted successfully.'));
        break;
      case 'generics':
        this.pharmacyService.deleteGeneric(id).subscribe(() => this.handleDelete('Generic information deleted successfully.'));
        break;
      case 'companies':
        this.pharmacyService.deleteCompany(id).subscribe(() => this.handleDelete('Medicine company deleted successfully.'));
        break;
      case 'customers':
        this.pharmacyService.deleteCustomer(id).subscribe(() => this.handleDelete('Customer information deleted successfully.'));
        break;
    }
  }

  displayCell(row: MasterRow, key: string): string {
    return String(row[key] ?? '-');
  }

  private handleDelete(message: string): void {
    this.notificationService.success(message);
    this.resetForm();
    this.loadPage();
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

  private applyResponse<T extends object>(response: PaginatedResponse<T>): void {
    this.rows = response.items as MasterRow[];
    this.total = response.total;
    this.page = response.page;
    this.pageSize = response.page_size;
  }

  private buildForm() {
    const group: Record<string, ReturnType<FormBuilder['control']>> = {};
    for (const field of this.config.fields) {
      group[field.key] = this.fb.control('', field.required ? Validators.required : []);
    }
    return this.fb.group(group);
  }

  private emptyFormValue(): Record<string, string> {
    return this.config.fields.reduce<Record<string, string>>((acc, field) => {
      acc[field.key] = '';
      return acc;
    }, {});
  }

  private extractFormValue(row: MasterRow): Record<string, string> {
    return this.config.fields.reduce<Record<string, string>>((acc, field) => {
      acc[field.key] = String(row[field.key] ?? '');
      return acc;
    }, {});
  }

  private buildMasterPayload(): MasterPayload {
    const value = this.form.getRawValue();
    return {
      name: String(value['name'] ?? '').trim(),
      description: this.optionalString(value['description']),
    };
  }

  private buildCompanyPayload(): CompanyPayload {
    const value = this.form.getRawValue();
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
    const value = this.form.getRawValue();
    return {
      patient_id: this.optionalString(value['patient_id']),
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
