import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { NotificationService } from '../../../../core/services/notification.service';
import { PharmacyDispense } from '../../models/pharmacy.models';
import { PharmacyService } from '../../services/pharmacy.service';

@Component({
  selector: 'app-pharmacy-dispense',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './pharmacy-dispense.component.html',
})
export class PharmacyDispenseComponent {
  private readonly fb = inject(FormBuilder);
  private readonly pharmacyService = inject(PharmacyService);
  private readonly notificationService = inject(NotificationService);

  dispenses: PharmacyDispense[] = [];
  resultMessage = '';

  readonly form = this.fb.group({
    prescription_ref: [''],
    medicine_name: ['', Validators.required],
    quantity: [1, Validators.required],
    unit_price: [0, Validators.required],
    note: [''],
  });

  constructor() {
    this.loadDispenses();
  }

  loadDispenses(): void {
    this.pharmacyService.list().subscribe((dispenses) => (this.dispenses = dispenses));
  }

  submit(): void {
    if (this.form.invalid) {
      return;
    }

    this.pharmacyService.dispense(this.form.getRawValue() as never).subscribe({
      next: (result) => {
        this.resultMessage = `Dispensed ${result.medicine_name}. Total ${result.total_price}`;
        this.form.reset({ prescription_ref: '', medicine_name: '', quantity: 1, unit_price: 0, note: '' });
        this.loadDispenses();
        this.notificationService.success(`Dispensed ${result.medicine_name} successfully.`);
      },
    });
  }
}
