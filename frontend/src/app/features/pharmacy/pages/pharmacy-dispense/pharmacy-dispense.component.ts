import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { PatientContextPanelComponent } from '../../../../shared/components/patient-context-panel/patient-context-panel.component';
import { PharmacyDispense, PharmacyPendingPrescription, PharmacySummary } from '../../models/pharmacy.models';
import { PharmacyService } from '../../services/pharmacy.service';

@Component({
  selector: 'app-pharmacy-dispense',
  standalone: true,
  imports: [CommonModule, FormsModule, PatientContextPanelComponent],
  templateUrl: './pharmacy-dispense.component.html',
  styleUrls: ['./pharmacy-dispense.component.scss'],
})
export class PharmacyDispenseComponent {
  private readonly pharmacyService = inject(PharmacyService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  summary: PharmacySummary | null = null;
  dispenses: PharmacyDispense[] = [];
  pendingPrescriptions: PharmacyPendingPrescription[] = [];
  queueSearch = '';
  historySearch = '';
  contextPatientId = '';

  constructor() {
    this.route.queryParamMap.subscribe((params) => {
      this.contextPatientId = params.get('patientId') || '';
    });
    this.loadAll();
  }

  loadAll(): void {
    this.loadSummary();
    this.loadDispenses();
    this.loadPendingPrescriptions();
  }

  loadSummary(): void {
    this.pharmacyService.getSummary().subscribe((summary) => (this.summary = summary));
  }

  loadDispenses(): void {
    this.pharmacyService.list().subscribe((dispenses) => (this.dispenses = dispenses));
  }

  loadPendingPrescriptions(): void {
    this.pharmacyService.listPendingPrescriptions().subscribe((orders) => (this.pendingPrescriptions = orders));
  }

  formatCurrency(value: string | number): string {
    return new Intl.NumberFormat('en-BD', {
      style: 'currency',
      currency: 'BDT',
      minimumFractionDigits: 2,
    }).format(Number(value || 0));
  }

  get filteredPendingPrescriptions(): PharmacyPendingPrescription[] {
    const query = this.queueSearch.trim().toLowerCase();
    return this.pendingPrescriptions.filter((item) =>
      (!this.contextPatientId || item.patient_id === this.contextPatientId) &&
      (!query ||
      [
        item.visit_number,
        item.patient_number,
        item.patient_name,
        item.doctor_name,
        item.item_name,
        item.chief_complaint,
        item.diagnosis,
      ]
        .filter(Boolean)
        .some((value) => value!.toLowerCase().includes(query)))
    );
  }

  get filteredDispenses(): PharmacyDispense[] {
    const query = this.historySearch.trim().toLowerCase();
    return this.dispenses.filter((item) =>
      (!this.contextPatientId || item.patient_id === this.contextPatientId) &&
      (!query ||
      [
        item.medicine_name,
        item.patient_name,
        item.patient_number,
        item.prescription_ref,
        item.visit_number,
        item.dispensed_by_name,
      ]
        .filter(Boolean)
        .some((value) => value!.toLowerCase().includes(query)))
    );
  }

  openWorkbench(orderId?: string, invoiceId?: string, dispenseId?: string): void {
    void this.router.navigate(['/pharmacy/dispense/workbench'], {
      queryParams: {
        orderId: orderId || undefined,
        invoiceId: invoiceId || undefined,
        dispenseId: dispenseId || undefined,
      },
    });
  }
}
