import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';

import { NotificationService } from '../../../../core/services/notification.service';
import { BillingService } from '../../models/billing.models';
import { BillingServiceApi } from '../../services/billing.service';

@Component({
  selector: 'app-billing-settings',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule],
  templateUrl: './billing-settings.component.html',
  styleUrls: ['./billing-settings.component.scss'],
})
export class BillingSettingsComponent {
  private readonly fb = inject(FormBuilder);
  private readonly billingService = inject(BillingServiceApi);
  private readonly notificationService = inject(NotificationService);

  loading = false;
  saving = false;
  services: BillingService[] = [];
  editorOpen = false;
  activeConfigType: 'global' | 'items' = 'global';
  serviceControls: Record<string, { max_discount_percentage: number | null; max_discount_amount: number | null; doctor_share_percentage: number; room_number: string; is_active: boolean }> = {};

  readonly form = this.fb.group({
    max_item_discount_percentage: [100, [Validators.required, Validators.min(0), Validators.max(100)]],
    max_item_discount_amount: [null as number | null, [Validators.min(0)]],
    max_invoice_discount_percentage: [100, [Validators.required, Validators.min(0), Validators.max(100)]],
    max_invoice_discount_amount: [null as number | null, [Validators.min(0)]],
    default_referral_percentage: [0, [Validators.required, Validators.min(0), Validators.max(100)]],
  });

  constructor() {
    this.loadPage();
  }

  loadPage(): void {
    this.loading = true;
    this.billingService.getSettings().subscribe({
      next: (settings) => {
        this.form.patchValue({
          max_item_discount_percentage: Number(settings.max_item_discount_percentage ?? 100),
          max_item_discount_amount: settings.max_item_discount_amount === null || settings.max_item_discount_amount === undefined ? null : Number(settings.max_item_discount_amount),
          max_invoice_discount_percentage: Number(settings.max_invoice_discount_percentage ?? 100),
          max_invoice_discount_amount: settings.max_invoice_discount_amount === null || settings.max_invoice_discount_amount === undefined ? null : Number(settings.max_invoice_discount_amount),
          default_referral_percentage: Number(settings.default_referral_percentage ?? 0),
        });
      },
      error: () => {
        this.loading = false;
      },
    });
    this.billingService.listServices().subscribe({
      next: (services) => {
        this.services = services;
        this.serviceControls = services.reduce((acc, service) => {
          acc[service.id] = {
            max_discount_percentage: service.max_discount_percentage === null || service.max_discount_percentage === undefined ? null : Number(service.max_discount_percentage),
            max_discount_amount: service.max_discount_amount === null || service.max_discount_amount === undefined ? null : Number(service.max_discount_amount),
            doctor_share_percentage: Number(service.doctor_share_percentage ?? 0),
            room_number: service.room_number ?? '',
            is_active: service.is_active,
          };
          return acc;
        }, {} as BillingSettingsComponent['serviceControls']);
        this.loading = false;
      },
      error: () => {
        this.loading = false;
      },
    });
  }

  openEditor(configType: 'global' | 'items'): void {
    this.activeConfigType = configType;
    this.editorOpen = true;
  }

  closeEditor(): void {
    this.editorOpen = false;
  }

  get isGlobalEditor(): boolean {
    return this.activeConfigType === 'global';
  }

  getConfigRows(): Array<{ key: 'global' | 'items'; label: string; description: string }> {
    return [
      {
        key: 'global',
        label: 'Global Invoice Controls',
        description: 'Default item discount caps, invoice discount caps, and default referral percentage.',
      },
      {
        key: 'items',
        label: 'Item Level Billing Controls',
        description: 'Per-service discount cap, referral percentage, investigation room, and active status.',
      },
    ];
  }

  save(): void {
    if (this.form.invalid || this.saving) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving = true;
    const value = this.form.getRawValue();
    this.billingService
      .updateSettings({
        max_item_discount_percentage: Number(value.max_item_discount_percentage ?? 0),
        max_item_discount_amount: value.max_item_discount_amount === null || value.max_item_discount_amount === undefined ? null : Number(value.max_item_discount_amount),
        max_invoice_discount_percentage: Number(value.max_invoice_discount_percentage ?? 0),
        max_invoice_discount_amount: value.max_invoice_discount_amount === null || value.max_invoice_discount_amount === undefined ? null : Number(value.max_invoice_discount_amount),
        default_referral_percentage: Number(value.default_referral_percentage ?? 0),
      })
      .subscribe({
        next: () => {
          this.saving = false;
          this.editorOpen = false;
          this.notificationService.success('Billing settings updated.');
        },
        error: () => {
          this.saving = false;
        },
      });
  }

  saveServiceControls(service: BillingService): void {
    const controls = this.serviceControls[service.id];
    if (!controls || this.saving) {
      return;
    }
    this.saving = true;
    this.billingService.updateServiceControls(service.id, {
      max_discount_percentage: controls.max_discount_percentage === null || controls.max_discount_percentage === undefined ? null : Number(controls.max_discount_percentage),
      max_discount_amount: controls.max_discount_amount === null || controls.max_discount_amount === undefined ? null : Number(controls.max_discount_amount),
      doctor_share_percentage: Number(controls.doctor_share_percentage ?? 0),
      room_number: controls.room_number?.trim() || null,
      is_active: controls.is_active,
    }).subscribe({
      next: (updated) => {
        this.saving = false;
        this.services = this.services.map((item) => item.id === updated.id ? updated : item);
        this.notificationService.success(`${updated.name} controls updated.`);
      },
      error: () => {
        this.saving = false;
      },
    });
  }

  formatCurrency(value: string): string {
    return new Intl.NumberFormat('en-BD', { style: 'currency', currency: 'BDT', minimumFractionDigits: 2 }).format(Number(value));
  }
}
