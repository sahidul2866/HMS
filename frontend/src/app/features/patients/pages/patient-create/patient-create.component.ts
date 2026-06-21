import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { debounceTime, distinctUntilChanged } from 'rxjs';

import { NotificationService } from '../../../../core/services/notification.service';
import { FormValidationUi } from '../../../../shared/utils/form-validation';
import { CreatePatientPayload, PatientLookupResult, PatientMobileLookup } from '../../models/patient.models';
import { PatientService } from '../../services/patient.service';

@Component({
  selector: 'app-patient-create',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './patient-create.component.html',
  styleUrls: ['./patient-create.component.scss'],
})
export class PatientCreateComponent {
  private readonly fb = inject(FormBuilder);
  private readonly patientService = inject(PatientService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly notificationService = inject(NotificationService);
  readonly validation = FormValidationUi;

  saving = false;
  submitted = false;
  private completed = false;
  lookupModalOpen = false;
  mobileLookup: PatientMobileLookup | null = null;
  mobileSearchResults: PatientLookupResult[] = [];
  mobileLookupMessage = '';

  readonly form = this.fb.group({
    first_name: ['', [Validators.required, Validators.minLength(2)]],
    last_name: ['', [Validators.required, Validators.minLength(2)]],
    phone: ['', [Validators.required, Validators.minLength(6)]],
    email: ['', Validators.email],
    gender: [''],
    date_of_birth: [''],
    address: [''],
    emergency_contact_name: [''],
    emergency_contact_phone: [''],
  });

  constructor() {
    this.form.controls.phone.valueChanges
      .pipe(debounceTime(350), distinctUntilChanged())
      .subscribe(() => this.searchMobile(false));
  }

  searchMobile(openMatches = true): void {
    const mobile = (this.form.getRawValue().phone || '').trim();
    if (mobile.length < 6) {
      this.mobileLookup = null;
      this.mobileSearchResults = [];
      this.mobileLookupMessage = '';
      this.lookupModalOpen = false;
      return;
    }
    this.patientService.lookupByMobile(mobile).subscribe({
      next: (lookup) => {
        this.mobileLookup = lookup;
        this.mobileSearchResults = lookup.patients;
        this.mobileLookupMessage = lookup.patients.length
          ? `${lookup.current_patient_count} of ${lookup.max_patients_allowed} patient slots already used for this mobile.`
          : `No patient found for this mobile yet. Limit is ${lookup.max_patients_allowed}.`;
        this.lookupModalOpen = openMatches && lookup.patients.length > 0;
      },
      error: () => {
        this.mobileLookup = null;
        this.mobileSearchResults = [];
        this.mobileLookupMessage = '';
        this.lookupModalOpen = false;
      },
    });
  }

  applyFamilyAutoFill(patient: PatientLookupResult): void {
    this.form.patchValue({
      phone: patient.phone || this.form.getRawValue().phone || '',
      address: patient.address || '',
      emergency_contact_name: patient.emergency_contact_name || '',
      emergency_contact_phone: patient.emergency_contact_phone || '',
    });
    this.mobileLookupMessage = `Loaded shared contact details from ${patient.full_name}.`;
    this.lookupModalOpen = false;
  }

  openLookupModal(): void {
    if (!this.mobileSearchResults.length) {
      return;
    }
    this.lookupModalOpen = true;
  }

  closeLookupModal(): void {
    this.lookupModalOpen = false;
  }

  cancel(): void {
    void this.router.navigate(['/patients']);
  }

  hasUnsavedChanges(): boolean {
    return !this.completed && !this.saving && this.form.dirty;
  }

  get patientDisplayName(): string {
    return `${this.form.getRawValue().first_name || ''} ${this.form.getRawValue().last_name || ''}`.trim() || 'New patient';
  }

  get mobileUsageTone(): 'ok' | 'warn' | 'full' {
    if (!this.mobileLookup) {
      return 'ok';
    }
    if (!this.mobileLookup.can_add_more) {
      return 'full';
    }
    return this.mobileLookup.current_patient_count > 0 ? 'warn' : 'ok';
  }

  submit(): void {
    this.submitted = true;
    if (this.form.invalid || this.saving) {
      this.form.markAllAsTouched();
      return;
    }

    this.saving = true;
    const payload: CreatePatientPayload = {
      first_name: this.form.getRawValue().first_name?.trim() || '',
      last_name: this.form.getRawValue().last_name?.trim() || '',
      phone: this.form.getRawValue().phone?.trim() || '',
      email: this.form.getRawValue().email?.trim() || null,
      gender: this.form.getRawValue().gender || null,
      date_of_birth: this.form.getRawValue().date_of_birth || null,
      address: this.form.getRawValue().address?.trim() || null,
      emergency_contact_name: this.form.getRawValue().emergency_contact_name?.trim() || null,
      emergency_contact_phone: this.form.getRawValue().emergency_contact_phone?.trim() || null,
    };
    this.patientService.create(payload).subscribe({
      next: (patient) => {
        this.saving = false;
        this.submitted = false;
        this.completed = true;
        this.form.markAsPristine();
        this.notificationService.success(`Patient ${patient.patient_number} created successfully.`);
        const returnTo = this.route.snapshot.queryParamMap.get('returnTo');
        if (returnTo) {
          void this.router.navigateByUrl(`${returnTo}?patientId=${patient.id}`);
          return;
        }
        void this.router.navigate(['/patients'], { queryParams: { createdPatientId: patient.id } });
      },
      error: () => {
        this.saving = false;
      },
    });
  }
}
