import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';

import { NotificationService } from '../../../../core/services/notification.service';
import { SessionService } from '../../../../core/services/session.service';
import { InvestigationWorkItem } from '../../models/laboratory.models';
import { LaboratoryServiceApi } from '../../services/laboratory.service';

@Component({
  selector: 'app-laboratory-overview',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './laboratory-overview.component.html',
})
export class LaboratoryOverviewComponent {
  private readonly laboratoryService = inject(LaboratoryServiceApi);
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
    this.laboratoryService.listWorklist().subscribe((items) => {
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
    this.laboratoryService.updateResult(this.selectedItem.order_id, this.resultForm.getRawValue() as never).subscribe((item) => {
      this.selectedItem = item;
      this.loadWorklist();
      this.notificationService.success(`Laboratory result for ${item.visit_number} updated.`);
    });
  }

  get summary(): { label: string; value: number }[] {
    return [
      { label: 'Pending Samples', value: this.worklist.filter((item) => item.status === 'pending').length },
      { label: 'In Progress', value: this.worklist.filter((item) => item.status === 'in_progress').length },
      { label: 'Completed', value: this.worklist.filter((item) => item.status === 'completed').length },
    ];
  }
}
