import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { debounceTime, distinctUntilChanged, of, switchMap } from 'rxjs';

import { AuthService, PatientRegistrationSearchResult } from '../../../../core/services/auth.service';
import { NotificationService } from '../../../../core/services/notification.service';

@Component({
  selector: 'app-patient-register',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, RouterLink],
  templateUrl: './patient-register.component.html',
  styleUrl: './patient-register.component.scss',
})
export class PatientRegisterComponent {
  private readonly fb = inject(FormBuilder);
  private readonly authService = inject(AuthService);
  private readonly notificationService = inject(NotificationService);
  private readonly router = inject(Router);

  loading = false;
  searching = false;
  errorMessage = '';
  showPassword = false;
  selectedPatient: PatientRegistrationSearchResult | null = null;
  searchResults: PatientRegistrationSearchResult[] = [];

  readonly form = this.fb.group({
    patient_id: [''],
    patient_search: [''],
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

  constructor() {
    this.form.controls.patient_search.valueChanges
      .pipe(
        debounceTime(250),
        distinctUntilChanged(),
        switchMap((value) => {
          const query = (value || '').trim();
          if (query.length < 2 || this.selectedPatient) {
            this.searchResults = [];
            this.searching = false;
            return of([]);
          }
          this.searching = true;
          return this.authService.searchPatientsForRegistration(query);
        })
      )
      .subscribe({
        next: (results) => {
          this.searching = false;
          this.searchResults = results;
        },
        error: () => {
          this.searching = false;
          this.searchResults = [];
        },
      });
  }

  togglePasswordVisibility(): void {
    this.showPassword = !this.showPassword;
  }

  selectPatient(patient: PatientRegistrationSearchResult): void {
    if (patient.has_portal_account) {
      this.errorMessage = 'This patient already has a portal account. Please sign in instead.';
      return;
    }
    this.selectedPatient = patient;
    this.searchResults = [];
    this.form.patchValue({
      patient_id: patient.id,
      patient_search: `${patient.full_name} (${patient.patient_number})`,
      full_name: patient.full_name,
      email: patient.email || this.form.controls.email.value || '',
      phone: patient.phone || this.form.controls.phone.value || '',
      gender: patient.gender || '',
      date_of_birth: patient.date_of_birth || '',
    });
    this.form.controls.full_name.disable();
    this.form.controls.phone.disable();
    this.form.controls.gender.disable();
    this.form.controls.date_of_birth.disable();
    this.errorMessage = '';
  }

  createAsNewPatient(): void {
    this.selectedPatient = null;
    this.searchResults = [];
    this.form.controls.full_name.enable();
    this.form.controls.phone.enable();
    this.form.controls.gender.enable();
    this.form.controls.date_of_birth.enable();
    this.form.patchValue({
      patient_id: '',
      patient_search: '',
      full_name: '',
      phone: '',
      gender: '',
      date_of_birth: '',
      address: '',
      emergency_contact_name: '',
      emergency_contact_phone: '',
    });
    this.errorMessage = '';
  }

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
