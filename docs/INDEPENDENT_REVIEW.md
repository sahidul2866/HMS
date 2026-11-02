# Independent ERP review (2026-10-31)

Scope of this pass: reproduce the handoff results, then probe billing money logic and IPD consolidation. It is **not** a full review of every module or an accessibility/design certification. Items marked *Confirmed* were reproduced by a test or run; *By reading* were read in code but not run.

## Reproduced baseline
| Check | Result |
|---|---|
| Backend `npm run test:erp:api` | 45 passed (before this pass) |
| Frontend tests | 28 passed |
| Production build | passes; `jsbarcode` CommonJS warning |
| Browser journey (superadmin only) | 13 stages passed, re-run after fixes also passed |
| GUI audit | 18 checks passed (9 routes × 2 viewports) |

## Defects found and FIXED (Confirmed by probes in `backend/tests/test_billing_review_probes.py`)
1. **High – fully returned invoice read as `paid`.** Total 100, paid 100, return all → `payment_status="paid"`, and the OPD visit's `consultation_payment_status` became `paid` again (consultation refunded but visit still passes payment gating). Now `returned`; a visit whose consultation lines are all returned gets `returned`. (`billing/service.py` `_recalculate_invoice_balance`, `_sync_opd_payment`)
2. **Medium – last line of a discounted invoice could not be returned** (per-line rounding exceeded the total by a cent: 3×3.33 with 10% → credits 9.00 vs total 8.99, rejected as "exceeds collected balance"). Invoice discount is now allocated by line with the remainder on the last line, so all returns sum to the total. (`_net_line_amounts`)
3. **High – IPD interim→final consolidation counted refunded money as still paid.** Interim paid 1000, refunded 400 → final showed paid 1000 instead of 600. Now carries net paid; plain refunds move with the receipts.
4. **High – consolidation silently dropped deposit surplus.** Deposit 1000 vs final 400: receipts 1000 but `paid_amount` capped at 400, 600 untraceable and unrefundable. Now `paid_amount` keeps it; new `overpaid_amount` field is returned and shown as "Refundable surplus" on the billing desk.
5. **Medium – items returned on an interim bill were billed again on the final draft.** Carry-forward now subtracts returned quantities.
6. **High – final bill re-priced interim lines at the current catalog price and lost the interim invoice-level discount.** Carried lines now reference the interim line (`carry_forward_item_id`) and keep its unit price and its net value after both item and invoice discounts (shown as the line discount); the interim discount reason is kept. A final bill must carry every outstanding interim line in full (422 `billing_carry_incomplete` otherwise), so billed charges can no longer be silently dropped while the interim bill is marked consolidated. Frontend passes the field through.

Tests: backend 51 passed + 1 expected xfail; frontend 28 passed; build and browser journey pass. Note: because a final bill must now carry every interim line in full, a deposit surplus can arise only through unusual paths; the surplus handling remains as a safety net.

## Open findings (NOT fixed)
| Sev | Status | Finding | Where |
|---|---|---|---|
| High | By reading | No bed-stay history: all unbilled days are billed at the admission's *current* bed rate, so transfers between rates misprice earlier days. Bed days use UTC dates, not hospital local time (UTC+6 shifts days up to 6 h). | `_calculate_ipd_billable_days` |
| High | By reading | Returns only move money. They do not cancel lab/radiology orders or restock pharmacy batches/FEFO. | `create_return` |
| Medium | Confirmed (xfail test) | A return cannot exceed money already collected, so lines on unpaid/partly paid invoices cannot be credited; cancelling them needs void/refund workarounds. | `create_return` |
| Medium | By reading | `GET /billing/reports/operations` writes a snapshot row on every call (side-effecting GET) and loads all invoices in range with lazy item/payment/refund loads (N+1, unbounded without dates). | `operations.statistics` |
| Medium | By reading | Interim returns' cash payouts stay on the inactive interim invoice, so report `collected − refunded` for consolidated admissions with returns does not reconcile. | consolidation |
| Medium | Confirmed | All ~130 routes are eagerly imported: single 2.41 MB `main.js` (419 kB gzip), no lazy loading. | `app.routes.ts` |
| Medium | Confirmed | GUI audit covers 9 of ~130 routes; browser journey uses superadmin only, so role/permission/branch UI paths are untested. | `frontend/e2e/*.cjs` |
| Low | By reading | `received_at`/`refunded_at` are client-supplied with no bound. Refund payout method is not tied to the original receipt method (card receipt refundable as cash). `/cash/balance` locks the user row on a GET. Refund-only users cannot submit cash handovers (endpoint needs `payment.collect`). | schemas, `operations.py` |
| Low | By reading | `IPDAdmission.billing_status` stays `cleared` after a post-clearance refund; discharge readiness recomputes live from invoices so discharge is still blocked correctly. | `create_refund` |

## Not verified / external prerequisites
Azure neural voice and physical PA audio; real barcode printer/scanner; real-paper print layout; lab/radiology/PACS/pharmacy return paths end to end; accounting integration, tax, insurance/corporate credit; migration backfill of old refunds/classifications; production-scale performance; multi-role browser journeys; responsive review at 768/1024 px; accessibility (focus, dialogs, labels).

## Production-readiness judgment
Not production ready for financial use until the two High open items (bed-rate history, return→fulfilment unwinding) are decided and fixed, and multi-role browser coverage exists.


## Second pass (2026-11-01) — IPD stay ledger, GUI cleanup, authorization

Reproduced: API 62 passed + 1 expected xfail (66 after my additions), frontend 30 passed, build passes (initial bundle now 2.54 MB / 427 kB gzip), `test:erp:browser`, `test:ipd:browser` (16 stages) and `test:gui:billing` pass when run sequentially after the build.

### New independent checks (Confirmed, all in `backend/tests`)
- **Randomised money invariants** (`test_random_payment_refund_return_sequences_keep_money_reconciled`): ~40 discounted multi-line invoices with random cash/card payments, refunds and partial returns. After every action: paid = receipts − refunds, due = max(0, total − returned − paid), returned ≤ total, per-receipt refunds ≤ receipt, cash custody = cash receipts − cash payouts. No violation found.
- **Cross-branch isolation** (`test_other_branch_user_cannot_read_or_change_an_invoice`): read, pay, refund, return, amend, history and void all rejected for a user of another branch.
- **Route authorization audit** (486 backend routes): every route has a permission dependency except login/refresh/registration, patient-portal/bot routes (patient-token auth), health checks, self-service logout/reset-password and two machine-ingestion endpoints. All 129 frontend routes except login/register/profile carry permission data.

### Defects found and fixed this pass
1. **High – machine ingestion key.** `/lis/integration/results` and `/radiology/integration/orders/{id}/dicom` are unauthenticated apart from a shared key whose default is committed in source, compared with `!=`. Now compared in constant time, and the shipped default is refused (503) when `APP_ENV=production`. Tests: `test_machine_key.py`. Operators must still set a real `MACHINE_INTEGRATION_KEY`.
2. **Medium – invoice detail clipped amounts at 390 px.** Unit price/total columns were cut off with letters breaking ("Q T Y"). Lines now stack on narrow screens (`billing-desk.component.scss/.html`); screenshot `/tmp/hms-billing-layout/390-invoice-detail.png` before/after reviewed.

### New open findings
| Sev | Status | Finding |
|---|---|---|
| Medium | By reading | `build_ipd_admission_draft` (a GET) commits to the database (creates per-rate tariff catalog rows named "IPD Bed … @ rate"); catalog entries accumulate with every distinct bed/rate and drafts are not read-only. |
| Medium | By reading | A bed-charge day that was returned/credited on an interim bill is still treated as billed, so it can never be re-billed if the patient did stay. |
| Low | Confirmed | Payment step defaults "Collect Now" to 0 and repeats the patient name in the summary line (cosmetic). |
| Low | Confirmed | Stale `failed-request.json`/`failure.png` from earlier runs remain in `/tmp/hms-ipd-browser` and can mislead artifact review; the run's `report.json` shows 16 stages, 0 errors. |

Not done in this pass (unchanged gaps): restricted-role browser journeys, expanded-dialog and keyboard-only review of every module, accessibility certification, physical devices (printer, scanner, PA/Azure), lab/radiology/pharmacy return paths, accounting/tax/insurance, production data volumes. Previously listed open High items (returns do not unwind lab/radiology/pharmacy fulfilment; unpaid-invoice returns unsupported) remain open.


## Third pass (2026-11-01) — every seeded role

Method: short-lived local access tokens were minted for one existing dev user per seeded role (24 roles; no passwords read or changed), then exercised against the local backend and the Angular dev app. Re-run with `npm run test:roles:api` and `npm run test:roles:browser` (needs the dev servers running; creates synthetic `RoleFlow` records in the dev DB).

| Check | Scope | Result |
|---|---|---|
| Permission matrix (`backend/scripts/role_matrix.py`) | 175 parameterless GET routes × 24 roles, compared with each route's declared permissions | No leak (no role got 200 where it lacked the declared permission), no 5xx. The only "unexpected 403" cases are the intended doctor-wise OPD rule below |
| Connected journey by owning role (`backend/scripts/role_workflow.py`) | register → book → check-in → invoice → pay → call → consult → prescribe → admit to IPD → doctor/nurse notes → orders → final invoice → pay → discharge, 97 steps; each step first tried by 3–5 unrelated roles | 0 problems after the fix below; every outsider attempt was refused |
| Browser route journey (`frontend/e2e/role-journeys.cjs`) | 116 routes × 24 roles: 548 allowed loads, 2164 forbidden attempts | No forbidden route opened, no blank page, no page error, no 5xx, no horizontal overflow |

### Defects found and fixed
1. **High – a Doctor could not admit an OPD patient to IPD.** `POST /opd/visits/{id}/convert-to-ipd` required `ipd.admission.manage`, which only Admin/Super Admin hold; the Doctor and Nurse roles hold `ipd.admit` (the right the admission page, `POST /ipd/admissions` and the ER conversion use). The UI guard sent them to the admit form, and the final submit failed 403. Now `ipd.admit` *or* `ipd.admission.manage`; button and handler on the visit list match. Tests: `tests/test_role_permissions.py`.
2. **Medium – "Action needed: Your account does not have permission" toast on pages the role may open.** Pages such as Queue, Billing overview, OPD visits and Catering read lookup data the role cannot see (doctor list, report widgets, medicine catalogue, HR employees); each refused read produced a red toast (12 roles on Queue alone). The error interceptor now stays quiet for permission-gated GET refusals, still reports refused changes, and shows the server's own text for scope refusals. Spec: `forbidden-reads.spec.ts`.

### Verified after the fixes
API 83 passed (the earlier expected failure for unpaid-invoice returns now passes: the working tree changed on disk since my last pass, and the initial bundle is 772 kB, so routes are now lazy). Frontend 39 passed, build passes, `test:erp:browser`, `test:ipd:browser` and `test:gui:billing` exit 0.

### Observations — decide, not fixed
| Sev | Finding |
|---|---|
| Medium | Receptionist, Nurse, Doctor Assistant and Management hold `opd.view` but not the all-doctors permission, so `/opd/visits` and the OPD dashboard answer 403 ("Doctor-wise OPD access must be granted from administration"). The dashboard then shows 0 visits / BDT 0 beside the toast, which reads as real data. Either grant the permission to the front-desk roles or hide the numbers when the read is refused. |
| Medium | No separation of duties in billing: Receptionist holds `billing.invoice.create` and `billing.payment.collect`, so the front desk can post and collect an IPD *final* bill. Permissions are not stage-specific. |
| Low | The prescribing Doctor cannot load the pharmacy medicine catalogue (needs `pharmacy.view`), so medicine auto-suggest is empty; free text works. Granting it exposes the stock catalogue. |
| Low | Billing Staff opening Queue Center gets "outside your assigned operational scope" (no queue scope assigned); Admin opening Patient Portal gets "requires a patient account" (expected). |

Not covered by this pass: clicking through each role's create/edit dialogs in the browser (route loads and the API chain were covered, form submits by non-admin roles were not), mutations other than the journey above, keyboard-only and accessibility review, physical devices, accounting/tax/insurance.

## Fourth pass (2026-11-01) — whole ecosystem again

Method: backend suite, frontend unit suite and production build; API role matrix and the 97-step role workflow; eight browser suites; every-role route journeys; role-by-role browser write workflow; return role flow. The dev servers on 4200/8000 were left running and were not restarted, so newer backend code was exercised on a second local instance (port 8001, now stopped) through `HMS_API_BASE` (API scripts) and `HMS_API_PROXY` (browser journeys).

Confirmed defects, fixed, each with a regression check:

| # | Severity | Defect | Fix |
|---|----------|--------|-----|
| 1 | High | OPD billing draft chose the "consultation" line by fuzzy keyword/amount over every module. With a doctor fee of 0 a zero-priced stock item won and a 0.00 invoice was posted; with equal fees any doctor's price could be used. | Draft now uses the visit doctor's own consultation/follow-up fee entry; fuzzy match only for visits without a doctor and only among OPD/custom entries. `tests/test_opd_consultation_line.py` |
| 2 | Medium | `/inventory` Store Stock Value bar was scaled against the first store, not the largest: a 27,150,192 px wide element. | `barPercent` against the largest value, clamped 0–100. Caught by `test:gui:inventory`. |
| 3 | Low | `/pharmacy/stock-review` nested a second `.page-body` inside the shell's; unused `RouterLink` import. | Root is `workspace-shell`; import removed. |
| 4 | Medium | Nurse, Doctor Assistant and Management were refused the OPD list/summary (all-doctors right missing), leaving a scope toast and zero dashboard numbers. | Right added to the three roles in `seed_data.py` and applied to the dev DB (Receptionist already had it). `tests/test_role_permissions.py` |
| 5 | Medium | Queue page always opened on OPD; a user whose assigned queue scope excludes it (Billing Staff) got a scope toast every poll. | New `GET /queue/scopes` (side-effect free scope test, no audit noise); page offers only readable queues and falls back to all if the endpoint is absent. `tests/test_queue_viewable_scopes.py` |
| 6 | Low | Admin opening My Portal got an error toast. | Overview call is quiet; page shows its "No patient profile linked" state. |
| 7 | Low | Doctor list was requested by roles the server refuses (12 roles on Queue). | `DoctorDirectoryService` skips the call without the gating rights. `lookup-requests.spec.ts` |

Tooling: `role_matrix.py` separates data-scope refusals from permission gaps; `role_workflow.py` cancels leftover synthetic queue tokens of aborted runs; `role-journeys.cjs` understands `permissionMode: 'any'` and lists refused lookup reads separately.

Results: backend 107 passed; frontend 41 passed; build clean (only the `jsbarcode` CommonJS warning); role matrix 0 problems; role workflow 97 steps 0 problems; every-role journeys 0/25 roles with problems; role write workflow, returns role flow, ERP/IPD/modules/dialogs/billing/UI browser suites pass.

Still open: the running dev backend must be restarted to serve `/queue/scopes` (until then `test:gui:inventory` flags a 404 on `/queue`, harmless because the page falls back); Doctor Assistant is refused two outpatient-dashboard reads by an assigned scope (by design); remaining quiet refused reads on `diagnostics/orders` and `billing/create`; doctors with fee 0 are billed the default 15.00 while the visit records 0; earlier-pass items (returns not unwinding lab/radiology, report GET writing a snapshot) are unchanged.

## Fifth pass (2026-11-01) — whole ecosystem again

Everything from the fourth pass was re-run, now including the support and specialist browser workflows and 30 roles. The dev servers were down, so they were started for the run and stopped afterwards.

Result: backend 135 passed, frontend 45 passed, build clean, role matrix 0 problems, role workflow 97 steps 0 problems, every browser suite passes, every-role journeys 0/30 roles with problems.

Defect found by `test:support:browser` (department-roster step) and fixed:

| Severity | Defect | Fix |
|----------|--------|-----|
| Medium | The persistent lookup cache (`ApiCacheService.getPersistent`) kept an answer for the whole tab session, including an empty list. A Department Head who opened the roster before HR created the first shift could never pick that shift (the dropdown stayed empty) until logging out. The same applied to the doctor list and other lookups. | Entries expire after 2 minutes, in memory and in session storage; empty lists are not stored; old-format entries are discarded. `testing/api-cache.spec.ts` |

Test fixes: `support-workflows.cjs` compared the salary field to the text `26000`, but the API returns `26000.00`; it now compares numerically.

Order note: `test:returns:gui` needs the role tokens written by `test:roles:browser` / `mint_role_tokens.py`; run it after one of those.

## Sixth pass (2026-11-01) — whole ecosystem again, plus Bangladesh billing

Re-run: backend 166 passed, frontend 45 passed, build clean, role matrix and 97-step role workflow clean on the current code, browser suites all pass except the transport pages (see below).

### Billing for the Bangladesh market

Audit of what already existed: item and invoice discounts by percentage with configurable caps and a mandatory reason; part payments with a running due, due-payment queue, receipts, refunds, returns; BDT formatting with lakh/crore grouping (`en-BD`); four payment methods.

Added (backend `schemas/billing.py`, `modules/billing/service.py`, `operations.py`, `utils/bdt.py`, migration `20261101_0075`; frontend billing create and desk):

| Area | Change |
|------|--------|
| Discounts | Flat **Taka** discount per item and for the whole invoice, as an alternative to the percentage (never both; entering one clears the other). Same caps, same mandatory reason, also on invoice amend. The stored percentage is the effective percentage. |
| Mobile banking | Provider (bKash, Nagad, Rocket, Upay, Other) and **TrxID** are required; the same TrxID cannot settle two receipts (unique per method and provider). |
| Card / bank | Card approval code and bank transfer / cheque number are required. Cash needs nothing. Format checked (letters, digits, - and /). |
| Receipts and invoices | Amount in words in Taka with lakh/crore ("Taka One Lakh Twenty Three Thousand ... and Paisa ... Only") from the server; the printed invoice lists each receipt with provider and reference; the desk shows them. |
| Part payment, then pay | Unchanged and verified: pay part at posting, collect the rest later from Due Payments, by any method, until paid. |

Tests: `backend/tests/test_billing_bangladesh.py` (21 cases) and `npm run test:billing:bd` (browser: Taka item and invoice discount, TrxID gate at posting and at the desk, bKash part payment, Nagad then cash to close, receipts and words).

Not implemented, by decision: VAT/tax lines and rounding to whole Taka. Most clinical services are exempt and the rules differ by service and branch; adding a tax line changes every total, return and refund calculation, so it needs a tax policy from the hospital first.

### Other findings

- Transport pages answer 500 against the dev database: `transport_requests.posting_policy` is missing. Migration `20261101_0074_operational_posting` (another change set) is recorded as applied but its columns are not in the dev database; it needs to be re-applied by its owner. Not touched here.
- My payment-reference migration was renumbered `0075` because two migrations were created as `0074` at the same time.
- A running dev backend must be restarted to serve the new billing fields; the older code simply ignores them.
