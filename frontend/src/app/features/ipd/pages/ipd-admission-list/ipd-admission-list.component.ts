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
  selectedAdmission: IPDAdmission | null = null;
  searchText = '';
  sortField: 'admission_number' | 'patient' | 'ward_bed' | 'doctor' | 'status' | 'admitted_at' = 'admitted_at';
  sortDirection: 'asc' | 'desc' = 'desc';

  constructor() {
    this.loadAdmissions();
  }

  loadAdmissions(): void {
    this.ipdService.listAdmissions().subscribe((rows) => (this.admissions = rows));
  }

  openAdmission(admission: IPDAdmission): void {
    this.selectedAdmission = admission;
  }

  closeAdmission(): void {
    this.selectedAdmission = null;
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
    const filtered = this.admissions.filter((admission) => {
      if (!q) return true;
      return (
        (admission.admission_number || '').toLowerCase().includes(q) ||
        `${admission.patient.first_name} ${admission.patient.last_name}`.toLowerCase().includes(q) ||
        (admission.patient.patient_number || '').toLowerCase().includes(q) ||
        (admission.attending_doctor_name || '').toLowerCase().includes(q) ||
        `${admission.ward_name || ''} ${admission.bed_number || ''}`.toLowerCase().includes(q)
      );
    });
    const dir = this.sortDirection === 'asc' ? 1 : -1;
    return [...filtered].sort((a, b) => {
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

  toggleSort(field: IPDAdmissionListComponent['sortField']): void {
    if (this.sortField === field) {
      this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
      return;
    }
    this.sortField = field;
    this.sortDirection = field === 'admitted_at' ? 'desc' : 'asc';
  }
}
