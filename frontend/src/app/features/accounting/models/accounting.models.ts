export interface AccountingJournal {
  id: string;
  journal_number: string;
  description: string;
  debit_amount: string;
  credit_amount: string;
  status: string;
}

export interface CreateJournalPayload {
  branch_id?: string | null;
  reference?: string | null;
  description: string;
  debit_amount: number;
  credit_amount: number;
}

