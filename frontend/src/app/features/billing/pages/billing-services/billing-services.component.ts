import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';

import { NotificationService } from '../../../../core/services/notification.service';
import { BillingService, CreateBillingServicePayload, UpdateBillingServiceControlsPayload } from '../../models/billing.models';
import { BillingServiceApi } from '../../services/billing.service';

@Component({
  selector: 'app-billing-services',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, FormsModule],
  templateUrl: './billing-services.component.html',
  styleUrls: ['./billing-services.component.scss'],
})
export class BillingServicesComponent {
  private readonly fb = inject(FormBuilder);
  private readonly billingService = inject(BillingServiceApi);
  private readonly notificationService = inject(NotificationService);
  private readonly router = inject(Router);

  services: BillingService[] = [];
  serviceModuleFilter: 'all' | 'laboratory' | 'radiology' | 'pharmacy' | 'ipd' | 'inventory' | 'opd' | 'custom' = 'all';
  sortField: 'code' | 'name' | 'module' | 'price' | 'doctor_share' | 'status' = 'name';
  sortDirection: 'asc' | 'desc' = 'asc';
  editingServiceId: string | null = null;
  savingServiceId: string | null = null;
  editDraft: UpdateBillingServiceControlsPayload = {
    doctor_share_percentage: 0,
    max_discount_percentage: null,
    max_discount_amount: null,
    room_number: null,
    is_active: true,
  };

  readonly form = this.fb.group({
    service_code: ['', Validators.required],
    name: ['', Validators.required],
    description: [''],
    unit_price: [0, [Validators.required, Validators.min(0.01)]],
    doctor_share_percentage: [0, [Validators.required, Validators.min(0), Validators.max(100)]],
  });

  constructor() {
    this.loadServices();
  }

  loadServices(): void {
    this.billingService.listServices().subscribe((services) => (this.services = services));
  }

  get filteredServices(): BillingService[] {
    const items =
      this.serviceModuleFilter === 'all'
        ? this.services
        : this.services.filter((item) => (item.source_module || '').toLowerCase() === this.serviceModuleFilter);
    const dir = this.sortDirection === 'asc' ? 1 : -1;
    return [...items].sort((a, b) => {
      switch (this.sortField) {
        case 'code':
          return dir * a.service_code.localeCompare(b.service_code);
        case 'module':
          return dir * (a.source_module || '').localeCompare(b.source_module || '');
        case 'price':
          return dir * (Number(a.unit_price || 0) - Number(b.unit_price || 0));
        case 'doctor_share':
          return dir * (Number(a.doctor_share_percentage || 0) - Number(b.doctor_share_percentage || 0));
        case 'status':
          return dir * Number(a.is_active) - dir * Number(b.is_active);
        case 'name':
        default:
          return dir * a.name.localeCompare(b.name);
      }
    });
  }

  toggleSort(field: BillingServicesComponent['sortField']): void {
    if (this.sortField === field) {
      this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
      return;
    }
    this.sortField = field;
    this.sortDirection = 'asc';
  }

  submit(): void {
    if (this.form.invalid) {
      return;
    }

    const payload: CreateBillingServicePayload = {
      service_code: this.form.getRawValue().service_code ?? '',
      name: this.form.getRawValue().name ?? '',
      description: this.form.getRawValue().description || null,
      unit_price: Number(this.form.getRawValue().unit_price ?? 0),
      doctor_share_percentage: Number(this.form.getRawValue().doctor_share_percentage ?? 0),
    };
    this.billingService.createService(payload).subscribe(() => {
      this.form.reset({
        service_code: '',
        name: '',
        description: '',
        unit_price: 0,
        doctor_share_percentage: 0,
      });
      this.loadServices();
      this.notificationService.success('Billing service saved successfully.');
    });
  }

  startEdit(service: BillingService): void {
    this.editingServiceId = service.id;
    this.editDraft = {
      doctor_share_percentage: Number(service.doctor_share_percentage || 0),
      max_discount_percentage: service.max_discount_percentage === null || service.max_discount_percentage === undefined ? null : Number(service.max_discount_percentage),
      max_discount_amount: service.max_discount_amount === null || service.max_discount_amount === undefined ? null : Number(service.max_discount_amount),
      room_number: service.room_number || null,
      is_active: service.is_active,
    };
  }

  cancelEdit(): void {
    this.editingServiceId = null;
    this.savingServiceId = null;
  }

  saveEdit(service: BillingService): void {
    if (this.savingServiceId) {
      return;
    }
    this.savingServiceId = service.id;
    const payload: UpdateBillingServiceControlsPayload = {
      doctor_share_percentage: Number(this.editDraft.doctor_share_percentage ?? 0),
      max_discount_percentage: this.editDraft.max_discount_percentage === null || this.editDraft.max_discount_percentage === undefined ? null : Number(this.editDraft.max_discount_percentage),
      max_discount_amount: this.editDraft.max_discount_amount === null || this.editDraft.max_discount_amount === undefined ? null : Number(this.editDraft.max_discount_amount),
      room_number: this.editDraft.room_number || null,
      is_active: this.editDraft.is_active ?? true,
    };
    this.billingService.updateServiceControls(service.id, payload).subscribe({
      next: () => {
        this.notificationService.success('Billing controls updated.');
        this.editingServiceId = null;
        this.savingServiceId = null;
        this.loadServices();
      },
      error: () => {
        this.savingServiceId = null;
      },
    });
  }

  openSourceModule(service: BillingService): void {
    const module = (service.source_module || '').toLowerCase();
    const route =
      module === 'laboratory'
        ? '/laboratory'
        : module === 'radiology'
        ? '/radiology'
        : module === 'pharmacy'
        ? '/pharmacy/settings'
        : module === 'ipd'
        ? '/ipd/settings'
        : module === 'opd'
        ? '/opd/settings'
        : module === 'inventory'
        ? '/inventory'
        : null;
    if (!route) {
      this.notificationService.warning('This is a custom billing item. No source module route.');
      return;
    }
    void this.router.navigate([route]);
  }

  formatCurrency(value: string): string {
    return new Intl.NumberFormat('en-BD', {
      style: 'currency',
      currency: 'BDT',
      minimumFractionDigits: 2,
    }).format(Number(value));
  }
}
