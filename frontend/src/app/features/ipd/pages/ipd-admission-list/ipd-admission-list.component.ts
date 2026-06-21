import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

import { PERMISSIONS } from '../../../../core/constants/permissions';
import { SessionService } from '../../../../core/services/session.service';
import { IPDAdmission } from '../../models/ipd.models';
import { IPDService } from '../../services/ipd.service';

@Component({
  selector: 'app-ipd-admission-list',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './ipd-admission-list.component.html',
  styleUrls: ['./ipd-admission-list.component.scss'],
})
export class IPDAdmissionListComponent {
  private readonly ipdService = inject(IPDService);
  private readonly router = inject(Router);
  readonly session = inject(SessionService);
  readonly permissions = PERMISSIONS;

  admissions: IPDAdmission[] = [];
  searchText = '';
  page = 1;
  pageSize = 12;
  sortField: 'admission_number' | 'patient' | 'ward_bed' | 'doctor' | 'status' | 'admitted_at' = 'admitted_at';
  sortDirection: 'asc' | 'desc' = 'desc';

  constructor() {
    this.loadAdmissions();
  }

  loadAdmissions(): void {
    this.ipdService.listAdmissions().subscribe((rows) => (this.admissions = rows));
  }

  openAdmission(admission: IPDAdmission): void {
    void this.router.navigate(['/ipd/admissions', admission.id]);
  }

  navigateToAdmission(): void {
    void this.router.navigate(['/ipd/admit']);
  }

  navigateToNewPatient(): void {
    void this.router.navigate(['/patients/new'], { queryParams: { returnTo: '/ipd/admit' } });
  }

  openBillingForAdmission(admission: IPDAdmission, stage: 'interim' | 'final' = 'interim'): void {
    void this.router.navigate(['/billing/create'], {
      queryParams: {
        patientId: admission.patient.id,
        ipdAdmissionId: admission.id,
        billingStage: stage,
      },
    });
  }

  get filteredAdmissions(): IPDAdmission[] {
    const q = this.searchText.trim().toLowerCase();
    return this.admissions.filter((admission) => {
      if (!q) return true;
      return (
        (admission.admission_number || '').toLowerCase().includes(q) ||
        `${admission.patient.first_name} ${admission.patient.last_name}`.toLowerCase().includes(q) ||
        (admission.patient.patient_number || '').toLowerCase().includes(q) ||
        (admission.attending_doctor_name || '').toLowerCase().includes(q) ||
        `${admission.ward_name || ''} ${admission.bed_number || ''}`.toLowerCase().includes(q)
      );
    });
  }

  get sortedAdmissions(): IPDAdmission[] {
    const dir = this.sortDirection === 'asc' ? 1 : -1;
    return [...this.filteredAdmissions].sort((a, b) => {
      switch (this.sortField) {
        case 'admission_number':
          return dir * (a.admission_number || '').localeCompare(b.admission_number || '');
        case 'patient':
          return dir * `${a.patient.first_name} ${a.patient.last_name}`.localeCompare(`${b.patient.first_name} ${b.patient.last_name}`);
        case 'ward_bed':
          return dir * `${a.ward_name || ''} ${a.bed_number || ''}`.localeCompare(`${b.ward_name || ''} ${b.bed_number || ''}`);
        case 'doctor':
          return dir * (a.attending_doctor_name || '').localeCompare(b.attending_doctor_name || '');
        case 'status':
          return dir * (a.status || '').localeCompare(b.status || '');
        case 'admitted_at':
        default:
          return dir * (new Date(a.admitted_at).getTime() - new Date(b.admitted_at).getTime());
      }
    });
  }

  get displayedAdmissions(): IPDAdmission[] {
    const start = (this.page - 1) * this.pageSize;
    return this.sortedAdmissions.slice(start, start + this.pageSize);
  }

  get totalPages(): number {
    return Math.max(Math.ceil(this.filteredAdmissions.length / this.pageSize), 1);
  }

  get rangeStart(): number {
    return this.filteredAdmissions.length ? (this.page - 1) * this.pageSize + 1 : 0;
  }

  get rangeEnd(): number {
    return Math.min(this.page * this.pageSize, this.filteredAdmissions.length);
  }

  onSearchChanged(): void {
    this.page = 1;
  }

  toggleSort(field: IPDAdmissionListComponent['sortField']): void {
    if (this.sortField === field) {
      this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
      this.page = 1;
      return;
    }
    this.sortField = field;
    this.sortDirection = field === 'admitted_at' ? 'desc' : 'asc';
    this.page = 1;
  }

  sortClass(field: IPDAdmissionListComponent['sortField']): string {
    return this.sortField === field ? `sorted-${this.sortDirection}` : '';
  }

  previousPage(): void {
    this.page = Math.max(this.page - 1, 1);
  }

  nextPage(): void {
    this.page = Math.min(this.page + 1, this.totalPages);
  }
}
