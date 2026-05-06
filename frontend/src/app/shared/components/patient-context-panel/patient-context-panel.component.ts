import { CommonModule } from '@angular/common';
import { Component, Input, OnChanges, SimpleChanges, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import {
  Patient,
  PatientClinicalHistory,
  PatientHistoryBillingInvoice,
  PatientHistoryOPDVisit,
  PatientHistoryOrder,
} from '../../../features/patients/models/patient.models';
import { PatientService } from '../../../features/patients/services/patient.service';

@Component({
  selector: 'app-patient-context-panel',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './patient-context-panel.component.html',
  styleUrls: ['./patient-context-panel.component.scss'],
})
export class PatientContextPanelComponent implements OnChanges {
  private readonly patientService = inject(PatientService);

  @Input() patient: Patient | null = null;
  @Input() patientId: string | null = null;
  @Input() history: PatientClinicalHistory | null = null;
  @Input() contextLabel = 'Patient Context';
  @Input() compact = false;

  loading = false;

  ngOnChanges(changes: SimpleChanges): void {
    if ((changes['patientId'] || changes['patient']) && !this.history) {
      this.loadHistory();
    }
  }

  get activePatient(): Patient | null {
    return this.history?.patient ?? this.patient;
  }

  get resolvedPatientId(): string | null {
    return this.patientId || this.activePatient?.id || null;
  }

  get patientName(): string {
    const patient = this.activePatient;
    return patient ? `${patient.first_name} ${patient.last_name}`.trim() : 'No patient selected';
  }

  get ageGenderLabel(): string {
    const patient = this.activePatient;
    if (!patient) return '-';
    return [this.ageLabel(patient.date_of_birth), patient.gender || null].filter(Boolean).join(' · ') || 'Demographics not recorded';
  }

  get activeAppointment() {
    return this.history?.appointments.find((item) => ['scheduled', 'confirmed', 'checked_in'].includes(item.status)) ?? null;
  }

  get activeAdmission() {
    return this.history?.ipd_admissions.find((item) => item.status !== 'discharged') ?? null;
  }

  get outstandingBills(): PatientHistoryBillingInvoice[] {
    return (this.history?.billing_invoices || []).filter((invoice) => Number(invoice.due_amount || 0) > 0);
  }

  get outstandingAmount(): number {
    return this.outstandingBills.reduce((sum, invoice) => sum + Number(invoice.due_amount || 0), 0);
  }

  get pendingLabOrders(): PatientHistoryOrder[] {
    return this.pendingOrdersByArea('laboratory', 'lab');
  }

  get pendingRadiologyOrders(): PatientHistoryOrder[] {
    return this.pendingOrdersByArea('radiology', 'imaging');
  }

  get currentPrescriptions(): PatientHistoryOrder[] {
    return this.allOrders.filter((order) => order.order_type === 'prescription' && !['cancelled', 'void'].includes(order.status)).slice(0, 4);
  }

  get recentVisits(): PatientHistoryOPDVisit[] {
    return [...(this.history?.opd_visits || [])]
      .sort((left, right) => String(right.visit_date).localeCompare(String(left.visit_date)))
      .slice(0, this.compact ? 2 : 4);
  }

  get alerts(): Array<{ label: string; tone: string }> {
    const alerts: Array<{ label: string; tone: string }> = [];
    if (this.outstandingAmount > 0) alerts.push({ label: `${this.formatCurrency(this.outstandingAmount)} outstanding`, tone: 'warning' });
    if (this.pendingLabOrders.length || this.pendingRadiologyOrders.length) alerts.push({ label: 'Pending diagnostics', tone: 'info' });
    if (this.activeAdmission) alerts.push({ label: `Admitted: ${this.activeAdmission.ward_name}/${this.activeAdmission.bed_number}`, tone: 'critical' });
    alerts.push({ label: 'Allergy info not recorded', tone: 'neutral' });
    return alerts.slice(0, this.compact ? 3 : 5);
  }

  get quickLinks(): Array<{ label: string; route: string; queryParams?: Record<string, string> }> {
    const patientId = this.resolvedPatientId;
    if (!patientId) return [];
    return [
      { label: 'Profile', route: `/patients/${patientId}` },
      { label: 'Appointment', route: '/appointments/create', queryParams: { patientId } },
      { label: 'OPD', route: '/opd/register', queryParams: { patientId } },
      { label: 'IPD', route: '/ipd/admit', queryParams: { patientId } },
      { label: 'Billing', route: '/billing/create', queryParams: { patientId } },
      { label: 'Lab', route: '/laboratory', queryParams: { patientId } },
      { label: 'Radiology', route: '/radiology', queryParams: { patientId } },
      { label: 'Pharmacy', route: '/pharmacy/dispense', queryParams: { patientId } },
      { label: 'Documents', route: `/patients/${patientId}`, queryParams: { section: 'documents' } },
    ];
  }

  formatCurrency(value: string | number): string {
    return new Intl.NumberFormat('en-BD', { style: 'currency', currency: 'BDT', maximumFractionDigits: 0 }).format(Number(value || 0));
  }

  private loadHistory(): void {
    const id = this.resolvedPatientId;
    if (!id) return;
    this.loading = true;
    this.patientService.getHistory(id).subscribe({
      next: (history) => {
        this.history = history;
        this.loading = false;
      },
      error: () => {
        this.loading = false;
      },
    });
  }

  private get allOrders(): PatientHistoryOrder[] {
    return (this.history?.opd_visits || []).flatMap((visit) => visit.orders);
  }

  private pendingOrdersByArea(...areas: string[]): PatientHistoryOrder[] {
    const areaSet = new Set(areas.map((area) => area.toLowerCase()));
    return this.allOrders.filter((order) => {
      const area = String(order.service_area || order.order_type || '').toLowerCase();
      return areaSet.has(area) && !['completed', 'verified', 'cancelled', 'void'].includes(order.status);
    });
  }

  private ageLabel(dateOfBirth?: string | null): string | null {
    if (!dateOfBirth) return null;
    const birth = new Date(dateOfBirth);
    if (Number.isNaN(birth.getTime())) return null;
    const today = new Date();
    let age = today.getFullYear() - birth.getFullYear();
    const monthDiff = today.getMonth() - birth.getMonth();
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) age -= 1;
    return `${age}y`;
  }
}
