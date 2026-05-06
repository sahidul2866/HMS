import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { NotificationService } from '../../../../core/services/notification.service';
import { SessionService } from '../../../../core/services/session.service';
import { PatientContextPanelComponent } from '../../../../shared/components/patient-context-panel/patient-context-panel.component';
import { printLaboratoryReport } from '../../../../shared/utils/laboratory-report-printer';
import { InvestigationWorkItem } from '../../models/laboratory.models';
import { LaboratoryServiceApi } from '../../services/laboratory.service';

@Component({
  selector: 'app-laboratory-workbench',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, PatientContextPanelComponent],
  templateUrl: './laboratory-workbench.component.html',
  styleUrls: ['./laboratory-workbench.component.scss'],
})
export class LaboratoryWorkbenchComponent {
  private readonly laboratoryService = inject(LaboratoryServiceApi);
  private readonly notificationService = inject(NotificationService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly fb = inject(FormBuilder);
  readonly sessionService = inject(SessionService);

  selectedItem: InvestigationWorkItem | null = null;
  loading = true;

  readonly resultForm = this.fb.group({
    status: ['collected'],
    sample_note: [''],
    result_text: [''],
  });

  constructor() {
    this.route.paramMap.subscribe((params) => {
      const orderId = params.get('orderId');
      if (!orderId) {
        void this.router.navigate(['/laboratory']);
        return;
      }
      this.loadItem(orderId);
    });
  }

  submitResult(): void {
    if (!this.selectedItem) {
      return;
    }
    this.laboratoryService.updateResult(this.selectedItem.order_id, this.resultForm.getRawValue() as never).subscribe((item) => {
      this.selectedItem = item;
      this.resultForm.patchValue({
        status: item.status,
        sample_note: item.sample_note || '',
        result_text: item.result_text || '',
      });
      this.notificationService.success(`Laboratory work item ${item.visit_number} updated.`);
    });
  }

  applyStatus(status: string): void {
    this.resultForm.patchValue({ status });
  }

  openQueue(): void {
    void this.router.navigate(['/laboratory']);
  }

  printReport(): void {
    if (!this.selectedItem) {
      return;
    }
    const printed = printLaboratoryReport({
      orderId: this.selectedItem.order_id,
      visitNumber: this.selectedItem.visit_number,
      patientNumber: this.selectedItem.patient_number,
      patientName: this.selectedItem.patient_name,
      doctorName: this.selectedItem.consulting_doctor_name,
      testName: this.selectedItem.item_name,
      roomNumber: this.selectedItem.room_number,
      sampleNote: this.selectedItem.sample_note,
      resultText: this.selectedItem.result_text,
      verifiedAt: this.selectedItem.verified_at,
    });
    if (!printed) {
      this.notificationService.warning('Unable to open print preview. Allow popups and try again.');
    }
  }

  get canPrintReport(): boolean {
    if (!this.selectedItem) {
      return false;
    }
    return ['verified', 'completed'].includes(this.selectedItem.status) && Boolean(this.selectedItem.result_text?.trim());
  }

  formatStatus(status: string): string {
    return status.replace('_', ' ').toUpperCase();
  }

  private loadItem(orderId: string): void {
    this.loading = true;
    this.laboratoryService.listWorklist().subscribe({
      next: (items) => {
        const item = items.find((entry) => entry.order_id === orderId) ?? null;
        this.selectedItem = item;
        this.loading = false;
        if (!item) {
          this.notificationService.warning('The selected laboratory item is no longer available in the active worklist.');
          void this.router.navigate(['/laboratory']);
          return;
        }
        this.resultForm.patchValue({
          status: item.status === 'pending' ? 'collected' : item.status,
          sample_note: item.sample_note || '',
          result_text: item.result_text || '',
        });
      },
      error: () => {
        this.loading = false;
      },
    });
  }
}
