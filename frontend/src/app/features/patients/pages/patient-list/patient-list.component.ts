import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { HasPermissionDirective } from '../../../../shared/directives/has-permission.directive';
import { PatientService } from '../../services/patient.service';
import { Patient } from '../../models/patient.models';

@Component({
  selector: 'app-patient-list',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, HasPermissionDirective],
  templateUrl: './patient-list.component.html',
  styleUrls: ['./patient-list.component.scss'],
})
export class PatientListComponent {
  private readonly patientService = inject(PatientService);
  private readonly router = inject(Router);

  patients: Patient[] = [];
  loading = true;
  searchText = '';
  sortField: 'patient_number' | 'name' | 'phone' | 'email' = 'patient_number';
  sortDirection: 'asc' | 'desc' = 'desc';

  constructor() {
    this.patientService.list().subscribe({
      next: (patients) => {
        this.patients = patients;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
      },
    });
  }

  openHistory(patient: Patient): void {
    void this.router.navigate(['/patients', patient.id]);
  }

  openBilling(patient: Patient): void {
    void this.router.navigate(['/billing/create'], { queryParams: { patientId: patient.id } });
  }

  openIpdAdmission(patient: Patient): void {
    void this.router.navigate(['/ipd/admit'], { queryParams: { patientId: patient.id } });
  }

  openOpdRegistration(patient: Patient): void {
    void this.router.navigate(['/opd/register'], { queryParams: { patientId: patient.id } });
  }

  get displayedPatients(): Patient[] {
    const q = this.searchText.trim().toLowerCase();
    const filtered = this.patients.filter((patient) => {
      if (!q) return true;
      return (
        (patient.patient_number || '').toLowerCase().includes(q) ||
        `${patient.first_name} ${patient.last_name}`.toLowerCase().includes(q) ||
        (patient.phone || '').toLowerCase().includes(q) ||
        (patient.email || '').toLowerCase().includes(q)
      );
    });
    const dir = this.sortDirection === 'asc' ? 1 : -1;
    return [...filtered].sort((a, b) => {
      switch (this.sortField) {
        case 'name':
          return dir * `${a.first_name} ${a.last_name}`.localeCompare(`${b.first_name} ${b.last_name}`);
        case 'phone':
          return dir * (a.phone || '').localeCompare(b.phone || '');
        case 'email':
          return dir * (a.email || '').localeCompare(b.email || '');
        case 'patient_number':
        default:
          return dir * (a.patient_number || '').localeCompare(b.patient_number || '');
      }
    });
  }

  toggleSort(field: PatientListComponent['sortField']): void {
    if (this.sortField === field) {
      this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
      return;
    }
    this.sortField = field;
    this.sortDirection = 'asc';
  }
}
