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

export interface AccountingKpi {
  label: string;
  value: string | number;
  tone: string;
  description?: string | null;
}

export interface ChartPoint {
  label: string;
  value: string | number;
}

export interface AccountingAlert {
  severity: string;
  title: string;
  message: string;
}

export interface AccountingDashboard {
  kpis: AccountingKpi[];
  revenue_vs_expense: ChartPoint[];
  department_revenue: ChartPoint[];
  payment_methods: ChartPoint[];
  expense_breakdown: ChartPoint[];
  due_aging: ChartPoint[];
  payable_aging: ChartPoint[];
  cash_flow: ChartPoint[];
  alerts: AccountingAlert[];
}

export interface Account {
  id: string;
  account_code: string;
  name: string;
  category: string;
  normal_balance: string;
  module_key?: string | null;
  current_balance: string | number;
  is_active: boolean;
}

export interface JournalEntryLine {
  id?: string;
  account_code: string;
  account_name: string;
  debit_amount: string | number;
  credit_amount: string | number;
}

export interface JournalEntry {
  id: string;
  journal_number: string;
  journal_date: string;
  source_module?: string | null;
  source_reference?: string | null;
  narration: string;
  status: string;
  total_debit: string | number;
  total_credit: string | number;
  lines: JournalEntryLine[];
  created_at: string;
}

export interface FinanceRecord {
  id: string;
  reference: string;
  name: string;
  amount: string | number;
  paid_amount: string | number;
  due_amount: string | number;
  category?: string | null;
  status: string;
  created_at: string;
}

export interface AccountingWorkspace {
  accounts: Account[];
  journal_entries: JournalEntry[];
  advances: FinanceRecord[];
  discounts: FinanceRecord[];
  refunds: FinanceRecord[];
  insurance_claims: FinanceRecord[];
  corporate_bills: FinanceRecord[];
  supplier_invoices: FinanceRecord[];
  expenses: FinanceRecord[];
  doctor_commissions: FinanceRecord[];
  cash_closings: FinanceRecord[];
  bank_transactions: FinanceRecord[];
}
