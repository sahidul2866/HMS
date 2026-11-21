# Accounting implementation and verification status

Updated 20 November 2026. This is a development delivery record, not a claim of completed Bangladesh statutory certification or production readiness.

## Implemented

The shared posting engine validates actual journal lines, enforces source idempotency and immutable posted entries, retains original entries and reversals in the ledger, and checks account scope and approved accounting policy. The database migration adds integrity guards without rewriting historical transactions. Cutover requires reviewed opening balances; unresolved historical summaries can be linked to posted or opening vouchers with an audit explanation. Source review never reconstructs historical cash, cost or liabilities from summary totals.

The hospital COA template, account hierarchy, effective policy approval, financial periods, close/reopen controls, maker-checker and year-end closing are available. Statements derive from posted GL movements. Trial balance shows ending debit/credit balances, with gross movements separately available. Reports include trial balance, profit and loss, balance sheet, cash flow, analysis exports and real numeric XLSX output. Entity details and policy version accompany statements.

Cashier shifts support physical counts and independent discrepancy approval. Transfers distinguish cash, bank and mobile/card clearing and explicit charges. CSV statement import creates no money; reconciliation requires exact account movement and preserves reversal review. Supplier payments require approved liabilities and cap outstanding amounts. Expense posting distinguishes accrual and disbursement. Tax vouchers require explicit approved effective rules; no statutory rate has been guessed.

Billing receipts, advance application, refunds, failed payment/chargeback adjustments, doctor principal/agent allocations and direct retention use source-aware posting. Pharmacy purchases post stock against goods-received clearing; supplier invoices match verified receipts. Pharmacy sales use actual collected amounts and verified weighted-average cost. Returns restore original cost, reduce unpaid receivables first, and place paid-sale credits in refund payable. The refund payment action discharges exactly that liability once with a verified channel/reference and independent approval where configured. The accounting screen exposes outstanding pharmacy refund payments.

Employee advances become recoverable only after actual disbursement. Payroll recovers verified receivables and uses configured payroll funding and attendance treatment. Inventory adjustments require reviewed approval under an active policy. Fixed assets link to an existing acquisition voucher and support straight-line depreciation and disposal.

The accounting screen also exposes employee advance disbursement, pending stock adjustment approval and historical summary reconciliation. Backend authorization remains authoritative, including the additional inventory permission.

## Migration

Migration `20261119_0078_accounting_controls.py` follows 0077. A local hms_dev backup was taken before applying it. Production was not migrated or deployed. Historical duplicate sources and summary-only records require reconciliation; installation does not repost or delete them. The existing billing and prescription changes remain in the workspace.

## Verification

Latest focused accounting run: **50 passed**. Targeted accounting plus operational run before the final two regressions: **64 passed**. Angular suite: **80 passed**, including transfer request reuse on retry. Final production build passed. A full backend/browser run recorded 407 passed and one prescription initial-page timeout while the shared static build was being replaced. All six browser cases were then rerun against an unchanged finished build; **6 passed** (49.76 seconds), including the previously timed-out follow-up prescription case. The preceding full run passed 406 tests before the last two regressions were added. Tests use isolated local PostgreSQL schemas, synthetic patients and two independent finance users.

The accounting browser acceptance flow exercises opening funds, actual OPD cash collection, physical cashier count, supervisor approval, statement import/matching, independent policy/journal approval, XLSX/PDF output and locked periods. The wider suites cover billing, prescriptions and operational posting. A synthetic 10,000-journal / 20,000-line statement benchmark is informational local evidence, not a production SLA.

## Remaining scope

This implementation does not complete every item in the original comprehensive request. Corporate/insurance agreements, credit limits, fully integrated panel collection/write-off workflows, multi-receipt purchase matching and purchase returns, recurring expense generation and binary document upload, asset department transfers and additional depreciation methods, interbranch/entity consolidation, official Mushak returns, all requested comparative/drilldown reports, and comprehensive browser acceptance of every role/workflow remain outstanding. Doctor settlement payment channel/reference capture also needs further standardization. Tax rules need qualified hospital-specific review against current official sources before use.

Warehouse and pharmacy valuation remain separate controls. Only weighted-average pharmacy valuation and straight-line asset depreciation are supported. Aging from operational summaries is not represented as a reconstructed historical as-of subledger. No assertion is made that 100 distinct accounting acceptance scenarios have been executed.

Final checks: `git diff --check` passed; local Alembic current is `20261119_0078 (head)`. The frontend production build passed after the final display corrections. Synthetic export artifacts are in [testing/accounting](testing/accounting/README.md).
