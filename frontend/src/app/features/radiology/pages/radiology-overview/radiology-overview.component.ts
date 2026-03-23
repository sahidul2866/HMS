import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';

import { NotificationService } from '../../../../core/services/notification.service';
import { SessionService } from '../../../../core/services/session.service';
import { InvestigationWorkItem } from '../../models/radiology.models';
import { RadiologyServiceApi } from '../../services/radiology.service';

@Component({
  selector: 'app-radiology-overview',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './radiology-overview.component.html',
})
export class RadiologyOverviewComponent {
  private readonly radiologyService = inject(RadiologyServiceApi);
  private readonly notificationService = inject(NotificationService);
  private readonly fb = inject(FormBuilder);
  readonly sessionService = inject(SessionService);

  worklist: InvestigationWorkItem[] = [];
  selectedItem: InvestigationWorkItem | null = null;

  readonly resultForm = this.fb.group({
    status: ['in_progress'],
    result_text: [''],
  });

  constructor() {
    this.loadWorklist();
  }

  loadWorklist(): void {
    this.radiologyService.listWorklist().subscribe((items) => {
      this.worklist = items;
      if (this.selectedItem) {
        this.selectedItem = items.find((item) => item.order_id === this.selectedItem?.order_id) ?? null;
      }
    });
  }

  selectItem(item: InvestigationWorkItem): void {
    this.selectedItem = item;
    this.resultForm.patchValue({
      status: item.status === 'pending' ? 'in_progress' : item.status,
      result_text: item.result_text || '',
    });
  }

  submitResult(): void {
    if (!this.selectedItem) {
      return;
    }
    this.radiologyService.updateResult(this.selectedItem.order_id, this.resultForm.getRawValue() as never).subscribe((item) => {
      this.selectedItem = item;
      this.loadWorklist();
      this.notificationService.success(`Radiology result for ${item.visit_number} updated.`);
    });
  }

  get summary(): { label: string; value: number }[] {
    return [
      { label: 'Pending Studies', value: this.worklist.filter((item) => item.status === 'pending').length },
      { label: 'In Progress', value: this.worklist.filter((item) => item.status === 'in_progress').length },
      { label: 'Completed', value: this.worklist.filter((item) => item.status === 'completed').length },
    ];
  }
}
