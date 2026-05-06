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
  page = 1;
  pageSize = 12;
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

  get filteredPatients(): Patient[] {
    const q = this.searchText.trim().toLowerCase();
    return this.patients.filter((patient) => {
      if (!q) return true;
      return (
        (patient.patient_number || '').toLowerCase().includes(q) ||
        `${patient.first_name} ${patient.last_name}`.toLowerCase().includes(q) ||
        (patient.phone || '').toLowerCase().includes(q) ||
        (patient.email || '').toLowerCase().includes(q)
      );
    });
  }

  get sortedPatients(): Patient[] {
    const dir = this.sortDirection === 'asc' ? 1 : -1;
    return [...this.filteredPatients].sort((a, b) => {
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

  get displayedPatients(): Patient[] {
    const start = (this.page - 1) * this.pageSize;
    return this.sortedPatients.slice(start, start + this.pageSize);
  }

  get totalPages(): number {
    return Math.max(Math.ceil(this.filteredPatients.length / this.pageSize), 1);
  }

  get rangeStart(): number {
    return this.filteredPatients.length ? (this.page - 1) * this.pageSize + 1 : 0;
  }

  get rangeEnd(): number {
    return Math.min(this.page * this.pageSize, this.filteredPatients.length);
  }

  onSearchChanged(): void {
    this.page = 1;
  }

  toggleSort(field: PatientListComponent['sortField']): void {
    if (this.sortField === field) {
      this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
      this.page = 1;
      return;
    }
    this.sortField = field;
    this.sortDirection = 'asc';
    this.page = 1;
  }

  sortClass(field: PatientListComponent['sortField']): string {
    return this.sortField === field ? `sorted-${this.sortDirection}` : '';
  }

  previousPage(): void {
    this.page = Math.max(this.page - 1, 1);
  }

  nextPage(): void {
    this.page = Math.min(this.page + 1, this.totalPages);
  }

  exportCsv(): void {
    const header = ['Patient No', 'Name', 'Phone', 'Email'];
    const rows = this.sortedPatients.map((patient) => [
      patient.patient_number,
      `${patient.first_name} ${patient.last_name}`.trim(),
      patient.phone || '',
      patient.email || '',
    ]);
    const csv = [header, ...rows].map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'patients.csv';
    anchor.click();
    URL.revokeObjectURL(url);
  }
}
