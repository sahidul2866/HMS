import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { AuthService } from '../../../../core/services/auth.service';
import { NotificationService } from '../../../../core/services/notification.service';

@Component({
  selector: 'app-patient-register',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  templateUrl: './patient-register.component.html',
})
export class PatientRegisterComponent {
  private readonly fb = inject(FormBuilder);
  private readonly authService = inject(AuthService);
  private readonly notificationService = inject(NotificationService);
  private readonly router = inject(Router);

  loading = false;
  errorMessage = '';

  readonly form = this.fb.group({
    full_name: ['', Validators.required],
    username: ['', Validators.required],
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required, Validators.minLength(8)]],
    phone: [''],
    gender: [''],
    date_of_birth: [''],
    address: [''],
    emergency_contact_name: [''],
    emergency_contact_phone: [''],
  });

  submit(): void {
    if (this.form.invalid || this.loading) {
      return;
    }
    this.loading = true;
    this.errorMessage = '';
    this.authService.registerPatient(this.form.getRawValue() as never).subscribe({
      next: (user) => {
        this.loading = false;
        this.notificationService.success('Patient account created.');
        void this.router.navigate([this.authService.getLandingRoute(user)]);
      },
      error: (error) => {
        this.loading = false;
        this.errorMessage = error.message ?? 'Unable to register';
      },
    });
  }
}
