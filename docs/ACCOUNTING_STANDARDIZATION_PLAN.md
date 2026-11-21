# Accounting standardization implementation plan

Request: complete accounting standardization within the existing HMS. Preserve the prior billing/prescription work and historical financial records. No production deployment.

## Findings from current code

- Two journal paths: legacy summary journals bypass the GL; operational modules call `_create_auto_entry`.
- Posting trusts header totals, permits negative/two-sided lines, guesses account category from debit/credit direction, and has no database immutability barrier.
- Reversed original entries disappear from GL/report queries even though reversing entries remain, causing incorrect net reports.
- Running balances ignore pre-filter opening movements; statements depend on mutable cached balances.
- Manual journal creation can bypass approval, period controls and source-reference concurrency protections.
- Historical sync mixes source logic, incorrectly treats some accruals as cash, and has no controlled cutover.
- Channels collapse into a single Cash / Bank account. Existing finance-record status changes do not post corresponding ledger events.
- COA has groups but lacks control-account posting restrictions. Periods, policy versions, approved effective tax configurations, proper shift/reconciliation and asset depreciation controls are missing.

## Implementation sequence

1. Central posting controls: line validation, exact amounts, account validation, idempotency, branch locking, audit, immutable posted records and safe reversals. Route legacy journal actions through GL.
2. Hierarchical editable hospital COA, localization, policy versions, cutover control, periods, approval segregation and reviewed opening journals. Preserve unknown legacy accounts for reconciliation; do not guess or repost them.
3. Channel-specific postings, shifts/closing, cash/bank transfers, settlement/reconciliation and advances; integrate source events atomically.
4. Doctor/referral allocation GL and settlement; supplier/AP/AR, expenses, payroll, pharmacy/inventory costing and returns; approved principal/agent policy and frozen mappings.
5. Effective-dated approved statutory configuration and assets/depreciation. No invented statutory rates or forms.
6. GL-derived reports, aging and reconciliation, filters, PDF/Excel exports, dashboard drill-downs and existing Angular accounting screens.
7. Execute new integration/API/database/browser tests plus existing billing/pharmacy/OPD/payroll regressions. Test migrations, rollback, concurrency and historic preservation. Back up local development DB before local migrations; no production migrations.

## Statutory reference checkpoints

Reviewed official sources on 2026-11-19: IFRS Foundation Bangladesh jurisdiction profile (https://www.ifrs.org/use-around-the-world/use-of-ifrs-standards-by-jurisdiction/view-jurisdiction/bangladesh/), FRC standards page (https://frc.gov.bd/site/page/7af9420d-7e55-4351-a8df-358fe97fa90a/site/page/%5Bfront%5D), NBR VAT rules directory (https://nbr.gov.bd/regulations/rules/vat-rules/eng) and authentic English VAT Rules text (https://nbr.gov.bd/uploads/news-scroller/Authentic_English_Text_VAT_Rules_2016.pdf). These identify authoritative configuration sources, not a determination of the hospital's legal status, service exemptions or applicable rates. Accountant review of entity-specific obligations and effective rules remains necessary.
