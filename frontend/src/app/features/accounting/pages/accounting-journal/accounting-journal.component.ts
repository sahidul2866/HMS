import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { NotificationService } from '../../../../core/services/notification.service';
import { AccountingJournal } from '../../models/accounting.models';
import { AccountingService } from '../../services/accounting.service';

@Component({
  selector: 'app-accounting-journal',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './accounting-journal.component.html',
})
export class AccountingJournalComponent {
  private readonly fb = inject(FormBuilder);
  private readonly accountingService = inject(AccountingService);
  private readonly notificationService = inject(NotificationService);

  journals: AccountingJournal[] = [];
  resultMessage = '';

  readonly form = this.fb.group({
    reference: [''],
    description: ['', Validators.required],
    debit_amount: [0, Validators.required],
    credit_amount: [0, Validators.required],
  });

  constructor() {
    this.loadJournals();
  }

  loadJournals(): void {
    this.accountingService.list().subscribe((journals) => (this.journals = journals));
  }

  submit(): void {
    if (this.form.invalid) {
      return;
    }

    this.accountingService.post(this.form.getRawValue() as never).subscribe({
      next: (journal) => {
        this.resultMessage = `Posted ${journal.journal_number}`;
        this.loadJournals();
        this.notificationService.success(`Journal ${journal.journal_number} posted successfully.`);
      },
    });
  }
}
