import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';

import { User } from '../../../../core/models/auth.models';
import { DoctorDirectoryService } from '../../../../core/services/doctor-directory.service';
import { NotificationService } from '../../../../core/services/notification.service';
import { Patient, PatientLookupResult } from '../../../patients/models/patient.models';
import { PatientService } from '../../../patients/services/patient.service';
import { ERService } from '../../services/er.service';

@Component({
  selector: 'app-er-register',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  template: `
    <section class="er-register">
      <header class="page-header">
        <div>
          <h1>Register ER Arrival</h1>
          <p>Capture urgent arrival details, triage category, and assignment preferences.</p>
        </div>
      </header>

      <form [formGroup]="form" (ngSubmit)="submit()" class="register-form">
        <div class="validation-summary" *ngIf="submitted && missingRequiredFields.length">
          <strong>Required before saving:</strong>
          <span>{{ missingRequiredFields.join(', ') }}</span>
        </div>

        <div class="field-group" [class.invalid-field]="controlInvalid('patient_id')">
          <label for="er-patient">Patient <span class="required-marker">Required</span></label>
          <input id="er-patient" type="text" [value]="patientLookup" placeholder="Search patient name or number" (input)="searchPatients($any($event.target).value)" />
          <small class="field-error" *ngIf="controlInvalid('patient_id')">Select a patient from the search results.</small>
          <ul class="lookup-list" *ngIf="patientLookupResults.length">
            <li *ngFor="let patient of patientLookupResults" (click)="applyPatient(patient)">
              {{ patient.patient_number }} - {{ patient.full_name }}
            </li>
          </ul>
        </div>

        <div class="field-grid">
          <label [class.invalid-field]="controlInvalid('arrival_mode')" for="er-arrival-mode">
            Arrival Mode <span class="required-marker">Required</span>
            <select formControlName="arrival_mode">
              <option value="walk_in">Walk-in</option>
              <option value="ambulance">Ambulance</option>
              <option value="transfer">Transfer</option>
            </select>
            <small class="field-error" *ngIf="controlInvalid('arrival_mode')">Arrival mode is required.</small>
          </label>
          <label [class.invalid-field]="controlInvalid('arrival_time')" for="er-arrival-time">
            Arrival Time <span class="required-marker">Required</span>
            <input type="datetime-local" formControlName="arrival_time" />
            <small class="field-error" *ngIf="controlInvalid('arrival_time')">Arrival time is required.</small>
          </label>
        </div>

        <div class="field-grid">
          <label [class.invalid-field]="controlInvalid('triage_category')">
            Triage Category <span class="required-marker">Required</span>
            <select formControlName="triage_category">
              <option value="red">Red</option>
              <option value="orange">Orange</option>
              <option value="yellow">Yellow</option>
              <option value="green">Green</option>
              <option value="blue">Blue</option>
            </select>
            <small class="field-error" *ngIf="controlInvalid('triage_category')">Triage category is required.</small>
          </label>
          <label [class.invalid-field]="controlInvalid('triage_level')">
            Triage Level <span class="required-marker">Required</span>
            <input type="number" formControlName="triage_level" min="1" max="5" />
            <small class="field-error" *ngIf="controlInvalid('triage_level')">Enter a triage level from 1 to 5.</small>
          </label>
        </div>

        <div class="field-grid">
          <label>
            Preferred Doctor
            <input type="text" [value]="doctorLookup" placeholder="Search doctor by name, email, specialty" (input)="searchDoctor($any($event.target).value)" />
            <ul class="lookup-list" *ngIf="doctorLookup && filteredDoctors.length">
              <li *ngFor="let doctor of filteredDoctors" (click)="applyDoctor(doctor)">
                {{ doctor.full_name }} <span>{{ doctor.email }}</span>
              </li>
            </ul>
          </label>
          <label>
            Assigned Nurse
            <input type="text" [value]="nurseLookup" placeholder="Search nurse or staff by name/email" (input)="searchNurse($any($event.target).value)" />
            <ul class="lookup-list" *ngIf="nurseLookup && filteredNurses.length">
              <li *ngFor="let nurse of filteredNurses" (click)="applyNurse(nurse)">
                {{ nurse.full_name }} <span>{{ nurse.email }}</span>
              </li>
            </ul>
          </label>
        </div>

        <label>
          Chief Complaint
          <textarea formControlName="chief_complaint"></textarea>
        </label>

        <label>
          Initial Diagnosis
          <textarea formControlName="initial_diagnosis"></textarea>
        </label>

        <label>
          Emergency Contact Name
          <input type="text" formControlName="emergency_contact_name" />
        </label>
        <label>
          Emergency Contact Phone
          <input type="text" formControlName="emergency_contact_phone" />
        </label>

        <button type="submit">Save ER Arrival</button>
      </form>
    </section>
  `,
  styles: [
    ".er-register { display: grid; gap: 1rem; }",
    ".page-header { display: flex; gap: 1rem; align-items: baseline; }",
    ".register-form { display: grid; gap: 1rem; }",
    ".field-grid { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }",
    ".lookup-list { border: 1px solid var(--border); border-radius: 0.5rem; background: var(--surface); max-height: 180px; overflow-y: auto; margin: 0; padding: 0; list-style: none; }",
    ".lookup-list li { display: grid; gap: 0.15rem; padding: 0.75rem; cursor: pointer; }",
    ".lookup-list li span { color: var(--text-muted); font-size: 0.78rem; }",
    ".lookup-list li:hover { background: var(--surface-emphasis); }",
    "label { display: grid; gap: 0.35rem; font-weight: 600; }",
    "input, select, textarea { width: 100%; padding: 0.75rem; border: 1px solid var(--border); border-radius: 0.5rem; }",
    ".required-marker { justify-self: start; border-radius: 999px; padding: 0.12rem 0.45rem; background: rgba(220, 38, 38, 0.09); color: #b91c1c; font-size: 0.7rem; font-weight: 800; }",
    ".invalid-field input, .invalid-field select, .invalid-field textarea, .field-group.invalid-field input { border-color: #dc2626; box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.1); }",
    ".field-error { color: #b91c1c; font-size: 0.78rem; font-weight: 700; }",
    ".validation-summary { display: grid; gap: 0.2rem; border: 1px solid rgba(220, 38, 38, 0.28); border-radius: 0.75rem; padding: 0.8rem 1rem; background: rgba(254, 242, 242, 0.9); color: #991b1b; }",
    "button { align-self: start; padding: 0.85rem 1.25rem; border: none; background: var(--primary); color: white; border-radius: 0.75rem; cursor: pointer; }",
    "button:disabled { opacity: 0.65; cursor: not-allowed; }",
  ],
})
export class ERRegisterComponent {
  private readonly fb = inject(FormBuilder);
  private readonly erService = inject(ERService);
  private readonly patientService = inject(PatientService);
  private readonly doctorDirectoryService = inject(DoctorDirectoryService);
  private readonly notificationService = inject(NotificationService);
  private readonly router = inject(Router);

  doctors: User[] = [];
  nurses: User[] = [];
  patientLookupResults: PatientLookupResult[] = [];
  patientLookup = '';
  doctorLookup = '';
  nurseLookup = '';
  submitted = false;

  readonly requiredFieldLabels: Record<string, string> = {
    patient_id: 'Patient',
    arrival_mode: 'Arrival Mode',
    arrival_time: 'Arrival Time',
    triage_category: 'Triage Category',
    triage_level: 'Triage Level',
  };

  readonly form = this.fb.group({
    patient_id: ['', Validators.required],
    arrival_mode: ['walk_in', Validators.required],
    arrival_time: [new Date().toISOString().slice(0, 16), Validators.required],
    triage_category: ['yellow', Validators.required],
    triage_level: [3, [Validators.required, Validators.min(1), Validators.max(5)]],
    preferred_doctor_user_id: [''],
    assigned_nurse_user_id: [''],
    assigned_location: [''],
    chief_complaint: [''],
    initial_diagnosis: [''],
    emergency_contact_name: [''],
    emergency_contact_phone: [''],
  });

  constructor() {
    this.loadReferenceData();
  }

  loadReferenceData(): void {
    this.doctorDirectoryService.listDoctors().subscribe((doctors) => {
      this.doctors = doctors;
      this.nurses = doctors;
    });
  }

  searchPatients(query: string): void {
    this.patientLookup = query.trim();
    if (this.patientLookup.length < 2) {
      this.patientLookupResults = [];
      return;
    }
    this.patientService.search(this.patientLookup).subscribe((results) => {
      this.patientLookupResults = results;
    });
  }

  applyPatient(patient: PatientLookupResult): void {
    this.form.patchValue({
      patient_id: patient.id,
      emergency_contact_name: patient.emergency_contact_name || '',
      emergency_contact_phone: patient.emergency_contact_phone || '',
    });
    this.patientLookup = `${patient.patient_number} - ${patient.full_name}`;
    this.patientLookupResults = [];
  }

  searchDoctor(query: string): void {
    this.doctorLookup = query.trim();
    if (!this.doctorLookup) {
      this.form.patchValue({ preferred_doctor_user_id: '' });
    }
  }

  searchNurse(query: string): void {
    this.nurseLookup = query.trim();
    if (!this.nurseLookup) {
      this.form.patchValue({ assigned_nurse_user_id: '' });
    }
  }

  get filteredDoctors(): User[] {
    return this.filterUsers(this.doctors, this.doctorLookup).slice(0, 8);
  }

  get filteredNurses(): User[] {
    return this.filterUsers(this.nurses, this.nurseLookup).slice(0, 8);
  }

  applyDoctor(doctor: User): void {
    this.form.patchValue({ preferred_doctor_user_id: doctor.id });
    this.doctorLookup = [doctor.full_name, doctor.email].filter(Boolean).join(' - ');
  }

  applyNurse(nurse: User): void {
    this.form.patchValue({ assigned_nurse_user_id: nurse.id });
    this.nurseLookup = [nurse.full_name, nurse.email].filter(Boolean).join(' - ');
  }

  get missingRequiredFields(): string[] {
    return Object.entries(this.requiredFieldLabels)
      .filter(([key]) => this.form.get(key)?.invalid)
      .map(([, label]) => label);
  }

  controlInvalid(controlName: string): boolean {
    const control = this.form.get(controlName);
    return !!control && control.invalid && (control.touched || this.submitted);
  }

  submit(): void {
    this.submitted = true;
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.notificationService.error(`Required before saving: ${this.missingRequiredFields.join(', ')}`);
      return;
    }

    const value = this.form.getRawValue();
    const payload = {
      patient_id: value.patient_id,
      arrival_mode: value.arrival_mode,
      arrival_time: this.toIsoDateTime(value.arrival_time || ''),
      triage_category: value.triage_category,
      triage_level: Number(value.triage_level || 3),
      chief_complaint: value.chief_complaint || null,
      initial_diagnosis: value.initial_diagnosis || null,
      emergency_contact_name: value.emergency_contact_name || null,
      emergency_contact_phone: value.emergency_contact_phone || null,
      preferred_doctor_user_id: value.preferred_doctor_user_id || null,
      assigned_nurse_user_id: value.assigned_nurse_user_id || null,
      assigned_location: value.assigned_location || null,
    };

    this.erService.createVisit(payload as never).subscribe({
      next: () => {
        this.notificationService.success('ER arrival registered successfully.');
        void this.router.navigate(['/er']);
      },
      error: (error: unknown) => this.notificationService.error(this.errorMessage(error)),
    });
  }

  private filterUsers(users: User[], query: string): User[] {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return users;
    return users.filter((user) =>
      [
        user.full_name,
        user.email,
        user.username,
        user.opd_prescription_header_specialty,
        user.opd_prescription_header_workplace,
      ]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(normalized))
    );
  }

  private toIsoDateTime(value: string): string {
    const date = value ? new Date(value) : new Date();
    return Number.isNaN(date.getTime()) ? new Date().toISOString() : date.toISOString();
  }

  private errorMessage(error: unknown): string {
    if (error instanceof HttpErrorResponse) {
      return error.error?.error?.message || error.error?.message || 'Failed to register ER arrival.';
    }
    return 'Failed to register ER arrival.';
  }
}
