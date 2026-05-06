import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { PERMISSIONS } from '../../../../core/constants/permissions';
import { User } from '../../../../core/models/auth.models';
import { DoctorDirectoryService } from '../../../../core/services/doctor-directory.service';
import { SessionService } from '../../../../core/services/session.service';
import { OPDVisit } from '../../models/opd.models';
import { OPDService } from '../../services/opd.service';

@Component({
  selector: 'app-opd-visit-list',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './opd-visit-list.component.html',
  styleUrls: ['./opd-visit-list.component.scss'],
})
export class OPDVisitListComponent {
  private readonly opdService = inject(OPDService);
  private readonly doctorDirectoryService = inject(DoctorDirectoryService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  readonly session = inject(SessionService);
  readonly permissions = PERMISSIONS;

  visits: OPDVisit[] = [];
  doctors: User[] = [];
  selectedDoctorUserId = '';
  searchText = '';
  selectedStatus = '';
  selectedPayment = '';
  selectedDate = '';
  selectedVisit: OPDVisit | null = null;
  page = 1;
  pageSize = 12;
  sortField: 'visit_number' | 'patient' | 'department' | 'doctor' | 'fee' | 'payment' | 'status' = 'visit_number';
  sortDirection: 'asc' | 'desc' = 'desc';

  constructor() {
    this.doctorDirectoryService.listDoctors().subscribe((doctors) => (this.doctors = doctors));
    this.loadVisits();
    this.route.queryParamMap.subscribe((params) => {
      const openVisit = params.get('openVisit');
      if (openVisit) {
        this.openVisit(openVisit);
      }
    });
  }

  loadVisits(): void {
    const doctorUserId = this.selectedDoctorUserId || null;
    this.opdService.listVisits(doctorUserId).subscribe((visits) => (this.visits = visits));
  }

  openVisit(visitId: string): void {
    this.opdService.getVisit(visitId).subscribe((visit) => {
      this.selectedVisit = visit;
    });
  }

  closeVisit(): void {
    this.selectedVisit = null;
  }

  navigateToRegisterVisit(): void {
    void this.router.navigate(['/opd/register']);
  }

  navigateToNewPatient(): void {
    void this.router.navigate(['/patients/new'], { queryParams: { returnTo: '/opd/register' } });
  }

  startVisit(visit: OPDVisit): void {
    if (!this.canStartVisit) return;
    void this.router.navigate(['/opd'], { queryParams: { openVisit: visit.id } });
  }

  openPayment(visit: OPDVisit): void {
    if (!this.session.hasPermission(PERMISSIONS.billingPaymentCollect)) return;
    void this.router.navigate(['/billing/create'], { queryParams: { opdVisitId: visit.id } });
  }

  isPaymentDone(visit: OPDVisit): boolean {
    return (visit.consultation_payment_status || '').toLowerCase() === 'paid';
  }

  formatCurrency(value: string | number | null | undefined): string {
    return `BDT ${Number(value || 0).toFixed(2)}`;
  }

  get filteredVisits(): OPDVisit[] {
    const search = this.searchText.trim().toLowerCase();
    return this.visits.filter((visit) => {
      const statusMatch = !this.selectedStatus || visit.status === this.selectedStatus;
      const paymentStatus = (visit.consultation_payment_status || 'unpaid').toLowerCase();
      const paymentMatch = !this.selectedPayment || paymentStatus === this.selectedPayment;
      const dateMatch = !this.selectedDate || visit.visit_date === this.selectedDate;
      const searchMatch =
        !search ||
        visit.visit_number.toLowerCase().includes(search) ||
        `${visit.patient.first_name} ${visit.patient.last_name}`.toLowerCase().includes(search) ||
        visit.patient.patient_number.toLowerCase().includes(search) ||
        (visit.consulting_doctor_name || '').toLowerCase().includes(search) ||
        (visit.department_name || '').toLowerCase().includes(search);
      return statusMatch && paymentMatch && dateMatch && searchMatch;
    });
  }

  get sortedVisits(): OPDVisit[] {
    const dir = this.sortDirection === 'asc' ? 1 : -1;
    return [...this.filteredVisits].sort((a, b) => {
      switch (this.sortField) {
        case 'patient':
          return dir * `${a.patient.first_name} ${a.patient.last_name}`.localeCompare(`${b.patient.first_name} ${b.patient.last_name}`);
        case 'department':
          return dir * (a.department_name || '').localeCompare(b.department_name || '');
        case 'doctor':
          return dir * (a.consulting_doctor_name || '').localeCompare(b.consulting_doctor_name || '');
        case 'fee':
          return dir * (Number(a.consultation_fee || 0) - Number(b.consultation_fee || 0));
        case 'payment':
          return dir * (Number(a.consultation_total || a.consultation_fee || 0) - Number(b.consultation_total || b.consultation_fee || 0));
        case 'status':
          return dir * (a.status || '').localeCompare(b.status || '');
        case 'visit_number':
        default:
          return dir * (a.visit_number || '').localeCompare(b.visit_number || '');
      }
    });
  }

  get displayedVisits(): OPDVisit[] {
    const start = (this.page - 1) * this.pageSize;
    return this.sortedVisits.slice(start, start + this.pageSize);
  }

  get totalPages(): number {
    return Math.max(Math.ceil(this.filteredVisits.length / this.pageSize), 1);
  }

  get rangeStart(): number {
    return this.filteredVisits.length ? (this.page - 1) * this.pageSize + 1 : 0;
  }

  get rangeEnd(): number {
    return Math.min(this.page * this.pageSize, this.filteredVisits.length);
  }

  onFiltersChanged(): void {
    this.page = 1;
  }

  toggleSort(field: OPDVisitListComponent['sortField']): void {
    if (this.sortField === field) {
      this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
      this.page = 1;
      return;
    }
    this.sortField = field;
    this.sortDirection = field === 'visit_number' ? 'desc' : 'asc';
    this.page = 1;
  }

  sortClass(field: OPDVisitListComponent['sortField']): string {
    return this.sortField === field ? `sorted-${this.sortDirection}` : '';
  }

  previousPage(): void {
    this.page = Math.max(this.page - 1, 1);
  }

  nextPage(): void {
    this.page = Math.min(this.page + 1, this.totalPages);
  }

  get canFilterByDoctor(): boolean {
    return this.session.hasPermission(PERMISSIONS.opdViewDoctorWise);
  }

  get canStartVisit(): boolean {
    const user = this.session.snapshot.user;
    return !!user?.roles?.some((role) => role.is_doctor_role || role.code === 'DOCTOR');
  }
}
