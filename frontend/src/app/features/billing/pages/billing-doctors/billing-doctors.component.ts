import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { NotificationService } from '../../../../core/services/notification.service';
import { CreateReferredDoctorPayload, ReferredDoctor } from '../../models/billing.models';
import { BillingServiceApi } from '../../services/billing.service';

@Component({
  selector: 'app-billing-doctors',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './billing-doctors.component.html',
  styleUrls: ['./billing-doctors.component.scss'],
})
export class BillingDoctorsComponent {
  private readonly fb = inject(FormBuilder);
  private readonly billingService = inject(BillingServiceApi);
  private readonly notificationService = inject(NotificationService);

  doctors: ReferredDoctor[] = [];

  readonly form = this.fb.group({
    doctor_code: ['', Validators.required],
    full_name: ['', Validators.required],
    specialty: [''],
    phone: [''],
    email: [''],
  });

  constructor() {
    this.loadDoctors();
  }

  loadDoctors(): void {
    this.billingService.listDoctors().subscribe((doctors) => (this.doctors = doctors));
  }

  submit(): void {
    if (this.form.invalid) {
      return;
    }

    const payload: CreateReferredDoctorPayload = {
      doctor_code: this.form.getRawValue().doctor_code ?? '',
      full_name: this.form.getRawValue().full_name ?? '',
      specialty: this.form.getRawValue().specialty || null,
      phone: this.form.getRawValue().phone || null,
      email: this.form.getRawValue().email || null,
    };
    this.billingService.createDoctor(payload).subscribe(() => {
      this.form.reset({ doctor_code: '', full_name: '', specialty: '', phone: '', email: '' });
      this.loadDoctors();
      this.notificationService.success('Referred doctor saved successfully.');
    });
  }
}
