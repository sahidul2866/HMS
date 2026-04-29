import { CommonModule } from '@angular/common';
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
        <div class="field-group">
          <label>Patient</label>
          <input type="text" [value]="patientLookup" placeholder="Search patient name or number" (input)="searchPatients($any($event.target).value)" />
          <ul class="lookup-list" *ngIf="patientLookupResults.length">
            <li *ngFor="let patient of patientLookupResults" (click)="applyPatient(patient)">
              {{ patient.patient_number }} - {{ patient.full_name }}
            </li>
          </ul>
        </div>

        <div class="field-grid">
          <label>
            Arrival Mode
            <select formControlName="arrival_mode">
              <option value="walk_in">Walk-in</option>
              <option value="ambulance">Ambulance</option>
              <option value="transfer">Transfer</option>
            </select>
          </label>
          <label>
            Arrival Time
            <input type="datetime-local" formControlName="arrival_time" />
          </label>
        </div>

        <div class="field-grid">
          <label>
            Triage Category
            <select formControlName="triage_category">
              <option value="red">Red</option>
              <option value="orange">Orange</option>
              <option value="yellow">Yellow</option>
              <option value="green">Green</option>
              <option value="blue">Blue</option>
            </select>
          </label>
          <label>
            Triage Level
            <input type="number" formControlName="triage_level" min="1" max="5" />
          </label>
        </div>

        <div class="field-grid">
          <label>
            Preferred Doctor
            <select formControlName="preferred_doctor_user_id">
              <option value="">Unassigned</option>
              <option *ngFor="let doctor of doctors" [value]="doctor.id">{{ doctor.full_name }}</option>
            </select>
          </label>
          <label>
            Assigned Nurse
            <select formControlName="assigned_nurse_user_id">
              <option value="">Unassigned</option>
              <option *ngFor="let nurse of nurses" [value]="nurse.id">{{ nurse.full_name }}</option>
            </select>
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

        <button type="submit" [disabled]="form.invalid">Save ER Arrival</button>
      </form>
    </section>
  `,
  styles: [
    ".er-register { display: grid; gap: 1rem; }",
    ".page-header { display: flex; gap: 1rem; align-items: baseline; }",
    ".register-form { display: grid; gap: 1rem; }",
    ".field-grid { display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); }",
    ".lookup-list { border: 1px solid var(--border); border-radius: 0.5rem; background: var(--surface); max-height: 180px; overflow-y: auto; margin: 0; padding: 0; list-style: none; }",
    ".lookup-list li { padding: 0.75rem; cursor: pointer; }",
    ".lookup-list li:hover { background: var(--surface-emphasis); }",
    "label { display: grid; gap: 0.35rem; font-weight: 600; }",
    "input, select, textarea { width: 100%; padding: 0.75rem; border: 1px solid var(--border); border-radius: 0.5rem; }",
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

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    const value = this.form.getRawValue();
    const payload = {
      ...value,
      preferred_doctor_user_id: value.preferred_doctor_user_id || null,
      assigned_nurse_user_id: value.assigned_nurse_user_id || null,
    };

    this.erService.createVisit(payload as never).subscribe({
      next: () => {
        this.notificationService.success('ER arrival registered successfully.');
        void this.router.navigate(['/er']);
      },
      error: () => this.notificationService.error('Failed to register ER arrival.'),
    });
  }
}
