# Hospital ERP ecosystem goal

Status: active. The built-in goal tracker failed with storage/transaction errors; this file is the persistent acceptance checklist.

## Objective

Make one connected, barcode-assisted patient journey work smoothly from registration to discharge, with automated regression checks and readable desktop/mobile layouts.

## Acceptance journey

1. Create a patient once and issue a resolvable patient barcode.
2. Book an available doctor appointment without duplicate slots.
3. Check in exactly once to an OPD visit and that doctor's daily serial.
4. Invoice and collect consultation payment without losing clinical state.
5. Call, recall, skip, and start the assigned patient; announce through the PA receiver.
6. Save clinical notes, prescribe medicines, order investigations, and print complete documents.
7. Resolve barcodes into the correct patient/visit/invoice/order, retaining context and enforcing access.
8. Bill additional orders without duplicate charges; pass work to diagnostics and pharmacy.
9. Convert to IPD exactly once with patient, doctor, diagnosis, bed, and financial links intact.
10. Record IPD care, orders, nursing/vitals/medication tasks, bed transfer, discharge planning, billing clearance, and discharge; release the bed correctly.
11. Keep billing intake and billing desk readable at desktop and mobile widths, with a clear patient → items → review/payment sequence.
12. Make the journey reproducible with synthetic data, assertions, screenshots, and useful failure reports.

## Current work

- Existing baseline: OPD-to-IPD API workflow tests, doctor queue concurrency, payment/refund synchronization, PA voice playback tests.
- In progress: browser-driven journey, IPD continuation, barcode handoffs, and billing GUI cleanup.
- External prerequisite: Azure neural voice synthesis requires server-side Azure Speech credentials; fallback remains visibly labelled.

Do not mark this goal complete until the acceptance checks have been exercised and remaining limitations are recorded honestly.

## Billing scope added by the user

Custom billing types/departments and catalog mappings; stored creator/discount data and transaction history; controlled invoice corrections; credited returns and printable vouchers; actual refund payout methods; saved reconciliation snapshots; cashier cash handover with variance and independent receiver acknowledgment. Implemented with migrations `20261031_0063` and `20261031_0064` and dedicated regression checks.

## Handoff status

Core connected journey implemented and exercised with local synthetic data. See `CLAUDE_HANDOFF.md` for exact browser/API coverage, commands, evidence, and independent whole-ERP/GUI review instructions. The broader ecosystem goal remains active: physical PA/printer verification, live Azure credentials, all staff-role GUI journeys and the wider accounting/diagnostics/consolidation scenarios require further independent assessment. Do not interpret this checklist as production certification.

Latest local evidence: 45 backend tests, 28 frontend tests, production build, 13 browser journey stages, 18 desktop/mobile route checks, and whitespace validation passed. Review `CLAUDE_HANDOFF.md` before continuing; external prerequisites and untested wider scenarios remain explicit.

IPD follow-up: see `IPD_MODULE.md`. Implemented bed turnover, stopped-treatment/task cleanup, receiving-staff acknowledgment, closed-record review, diagnostic verification handoffs and a dated bed-stay ledger. User selected one daily charge at the highest bed rate used that day, using Dhaka dates; historical unrecorded rates remain labelled estimates.
