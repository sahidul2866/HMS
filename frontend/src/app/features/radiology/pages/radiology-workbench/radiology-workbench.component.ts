import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { NotificationService } from '../../../../core/services/notification.service';
import { SessionService } from '../../../../core/services/session.service';
import { PatientContextPanelComponent } from '../../../../shared/components/patient-context-panel/patient-context-panel.component';
import { InvestigationWorkItem } from '../../models/radiology.models';
import { RadiologyServiceApi } from '../../services/radiology.service';

@Component({
  selector: 'app-radiology-workbench',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, PatientContextPanelComponent],
  templateUrl: './radiology-workbench.component.html',
  styleUrls: ['./radiology-workbench.component.scss'],
})
export class RadiologyWorkbenchComponent {
  private readonly radiologyService = inject(RadiologyServiceApi);
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
        void this.router.navigate(['/radiology']);
        return;
      }
      this.loadItem(orderId);
    });
  }

  submitResult(): void {
    if (!this.selectedItem) {
      return;
    }
    this.radiologyService.updateResult(this.selectedItem.order_id, this.resultForm.getRawValue() as never).subscribe((item) => {
      this.selectedItem = item;
      this.resultForm.patchValue({
        status: item.status,
        sample_note: item.sample_note || '',
        result_text: item.result_text || '',
      });
      this.notificationService.success(`Radiology work item ${item.visit_number} updated.`);
    });
  }

  applyStatus(status: string): void {
    this.resultForm.patchValue({ status });
  }

  openQueue(): void {
    void this.router.navigate(['/radiology']);
  }

  formatStatus(status: string): string {
    const normalized = status === 'collected' ? 'ready' : status;
    return normalized.replace('_', ' ').toUpperCase();
  }

  private loadItem(orderId: string): void {
    this.loading = true;
    this.radiologyService.listWorklist().subscribe({
      next: (items) => {
        const item = items.find((entry) => entry.order_id === orderId) ?? null;
        this.selectedItem = item;
        this.loading = false;
        if (!item) {
          this.notificationService.warning('The selected radiology item is no longer available in the active worklist.');
          void this.router.navigate(['/radiology']);
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
