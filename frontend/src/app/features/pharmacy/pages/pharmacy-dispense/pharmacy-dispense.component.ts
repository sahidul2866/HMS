import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

import { PharmacyDispense, PharmacyPendingPrescription, PharmacySummary } from '../../models/pharmacy.models';
import { PharmacyService } from '../../services/pharmacy.service';

@Component({
  selector: 'app-pharmacy-dispense',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './pharmacy-dispense.component.html',
  styleUrls: ['./pharmacy-dispense.component.scss'],
})
export class PharmacyDispenseComponent {
  private readonly pharmacyService = inject(PharmacyService);
  private readonly router = inject(Router);

  summary: PharmacySummary | null = null;
  dispenses: PharmacyDispense[] = [];
  pendingPrescriptions: PharmacyPendingPrescription[] = [];
  queueSearch = '';
  historySearch = '';

  constructor() {
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
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(Number(value || 0));
  }

  get filteredPendingPrescriptions(): PharmacyPendingPrescription[] {
    const query = this.queueSearch.trim().toLowerCase();
    if (!query) {
      return this.pendingPrescriptions;
    }
    return this.pendingPrescriptions.filter((item) =>
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
        .some((value) => value!.toLowerCase().includes(query))
    );
  }

  get filteredDispenses(): PharmacyDispense[] {
    const query = this.historySearch.trim().toLowerCase();
    if (!query) {
      return this.dispenses;
    }
    return this.dispenses.filter((item) =>
      [
        item.medicine_name,
        item.patient_name,
        item.patient_number,
        item.prescription_ref,
        item.visit_number,
        item.dispensed_by_name,
      ]
        .filter(Boolean)
        .some((value) => value!.toLowerCase().includes(query))
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
