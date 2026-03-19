import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { NotificationService } from '../../../../core/services/notification.service';
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
  private readonly route = inject(ActivatedRoute);
  private readonly notificationService = inject(NotificationService);

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
      next: (patient) => {
        this.saving = false;
        this.notificationService.success(`Patient ${patient.patient_number} created successfully.`);
        const returnTo = this.route.snapshot.queryParamMap.get('returnTo');
        if (returnTo) {
          void this.router.navigateByUrl(`${returnTo}?patientId=${patient.id}`);
          return;
        }
        void this.router.navigate(['/patients']);
      },
      error: () => {
        this.saving = false;
      },
    });
  }
}
