# Synthetic accounting acceptance artifacts

These PDF/XLSX statements come from the isolated browser acceptance workflow, not from hospital financial data. The workflow supplies opening capital of BDT 5,000, collects BDT 500 from an OPD patient, and posts an independently approved BDT 100 noncash receivable/revenue voucher. Ending debit and credit balances are each BDT 5,600; cash is BDT 5,500. The PDF was rendered and visually checked. The XLSX acceptance checks load the actual workbook and verify its numeric trial-balance total.

The JSON benchmark measures statement generation on a synthetic local PostgreSQL ledger with 10,000 journals and 20,000 lines. It is not a production latency guarantee.

See ../../ACCOUNTING_STANDARDIZATION_DELIVERY.md for implementation status, checks and remaining scope.
