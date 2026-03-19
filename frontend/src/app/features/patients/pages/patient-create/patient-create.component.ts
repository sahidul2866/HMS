import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';

import { CreatePatientPayload } from '../../models/patient.models';
import { PatientService } from '../../services/patient.service';

@Component({
  selector: 'app-patient-create',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './patient-create.component.html',
})
export class PatientCreateComponent {
  private readonly fb = inject(FormBuilder);
  private readonly patientService = inject(PatientService);
  private readonly router = inject(Router);

  saving = false;

  readonly form = this.fb.group({
    first_name: ['', Validators.required],
    last_name: ['', Validators.required],
    phone: [''],
    email: [''],
    gender: [''],
    date_of_birth: [''],
    address: [''],
    emergency_contact_name: [''],
    emergency_contact_phone: [''],
  });

  submit(): void {
    if (this.form.invalid || this.saving) {
      return;
    }

    this.saving = true;
    const payload: CreatePatientPayload = {
      first_name: this.form.getRawValue().first_name ?? '',
      last_name: this.form.getRawValue().last_name ?? '',
      phone: this.form.getRawValue().phone ?? null,
      email: this.form.getRawValue().email ?? null,
      gender: this.form.getRawValue().gender ?? null,
      date_of_birth: this.form.getRawValue().date_of_birth ?? null,
      address: this.form.getRawValue().address ?? null,
      emergency_contact_name: this.form.getRawValue().emergency_contact_name ?? null,
      emergency_contact_phone: this.form.getRawValue().emergency_contact_phone ?? null,
    };
    this.patientService.create(payload).subscribe({
      next: () => {
        this.saving = false;
        void this.router.navigate(['/patients']);
      },
      error: () => {
        this.saving = false;
      },
    });
  }
}
