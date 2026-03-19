import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { NotificationService } from '../../../../core/services/notification.service';
import { BillingService, CreateBillingServicePayload } from '../../models/billing.models';
import { BillingServiceApi } from '../../services/billing.service';

@Component({
  selector: 'app-billing-services',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './billing-services.component.html',
  styleUrls: ['./billing-services.component.scss'],
})
export class BillingServicesComponent {
  private readonly fb = inject(FormBuilder);
  private readonly billingService = inject(BillingServiceApi);
  private readonly notificationService = inject(NotificationService);

  services: BillingService[] = [];

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

  formatCurrency(value: string): string {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(Number(value));
  }
}
