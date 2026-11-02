# Automatic posting, payroll corrections and dietary coordination

This continuation connects recorded hospital operations to stock movements, cashier invoices and balanced accounting entries. It records in-app books; it does not execute an external bank/card/mobile-wallet transfer. All examples below are synthetic acceptance data.

## Posting rules

| Recorded event | Automatic result | Main controls |
| --- | --- | --- |
| New invoice | Patient receivable / hospital revenue | Actor and branch validation; historical prices/classifications retained |
| Delivered billable meal | Cashier invoice; receivable / catering revenue | Approved active diet, configured meal price; patient/admission ownership; immutable source link |
| Completed billable trip | Cashier invoice; receivable / transport revenue | Registered patient, manager-entered positive fare; fare fixed after completion/invoicing; driver cannot change it |
| Cashier receipt | Cash/bank book / patient receivable | Existing receipt permissions, payment-reference rules and due limits; source sync cannot repost it |
| Return credit and any payout | Charge-credit entry and separate cash payout entry | Existing departmental/quantity/permission checks; monetary credit does not automatically restock prepared food |
| Invoice discount amendment or unpaid void | Receivable adjustment entry | Append-only financial history; paid/returned invoice protections; final bills carrying earlier charges require reviewed reversal |
| Stock receiving | Physical store/item/batch receipt; inventory / goods-received clearing | Positive quantity, total = quantity × unit cost, branch ownership; no invented supplier payment |
| Start meal preparation | FEFO stock issues, store/item/batch reductions; kitchen consumption / inventory | Recipe item, store and quantity frozen on the ticket; active usable batches and sufficient physical store stock; transaction rollback on failure |
| Fuel record / completed maintenance | Vehicle expense / vehicle expense payable | Recorded cost, source ID and actor; no invented cash settlement; maintenance is accrued on completion |
| Served staff meal marked for payroll | Staff-meal receivable / catering revenue | Linked active employee, positive paid-meal amount, explicit payroll choice |
| Payroll approval | Salary expense / payroll payable, staff-meal recovery and deduction clearing | Independent reviewer; frozen employee/month totals; meals/adjustments reserved once |
| Payroll marked paid | Payroll payable / cash-bank book | Prior accrual required; replay does not repeat loan recovery or book movement; actual bank execution remains external |

The default account map is in `backend/app/modules/support_posting/service.py`: receivable 1100, cash/bank book 1001, inventory 1300, staff meal receivable 1150, payroll payable 2200, payroll deduction clearing 2300, receiving clearing 2400, vehicle expense payable 2450, revenue 4000/4300/4400, and expenses 5100/5200/5300/5310. Return/discount adjustments use 4100. Review this map against the hospital's chart before production use. Existing source-sync receipt references are preserved so an accountant sync cannot duplicate automatic receipts/refunds.

`operational_postings` holds a unique source-type/source-ID/event link to each invoice/journal and records actor/policy details. All writes use the caller's transaction. Branch/source locks serialize the critical transitions; no commit occurs halfway through a stock issue, delivery/invoice or payroll posting. A failed preparation does not leave reduced stock or a changed task stage. Automatic journals retain the operational actor as creator; they do not falsely claim a separate human GL approval.

Catering and transport invoices receive the corresponding branch billing classification and department, including per-item snapshots. Existing configured classifications are preserved; an inactive classification must be reviewed rather than silently bypassed. Billable plan amounts are authoritative. Package inclusion is not inferred: configure an included meal with a zero charge and a chargeable extra meal with its approved amount.

## Physical stock and prepared waste

The catering manager chooses a stock item, kitchen store and quantity per meal. The inventory manager creates/receives the item and batch. At generation, the ticket stores its consumption recipe; later plan changes do not change that ticket's quantity. Preparation splits consumption across valid batches in expiry order, records real stock issues/transactions, updates the store and global item balances and records the corresponding cost entry.

A prepared meal cancelled, refused, missed or held by a new NPO instruction remains **consumed/waste**. It is never automatically returned to saleable stock. Unprepared cancelled tickets consume nothing. Financial credits do not assert that food physically returned. The current recipe model maps one inventory SKU per meal plan; multi-ingredient recipe/BOM expansion is a separate enhancement.

Inventory first-use stores now persist stable IDs under a lock. Legacy main-store allocation only assigns a proven unallocated remainder; it cannot duplicate quantities already held in another store. Known foreign-branch items cannot be received/issued into this branch's stores.

## Payroll workflow

1. Payroll officer configures the employee's salary and requests an earning/deduction adjustment with a reason, target month and optional source paid item.
2. A different HR reviewer approves/rejects the request. An employee cannot approve their own correction. A correction to paid history targets a later month.
3. Calculation reserves approved adjustments and served payroll meals. A meal from an older date, served/recorded after its original payroll, can enter the next eligible calculation once; legacy review flags are excluded.
4. A late adjustment for an unapproved run can be approved and included through **Recalculate**. Recalculation releases/rebinds reservations, replaces only the unapproved working items, resets review and preserves an audit event. Approved, paid and locked runs cannot be recalculated.
5. A different HR reviewer approves, records payment and locks the run. Meal deductions and adjustments become applied on payment. Cancellation before payment releases reservations; an already posted accrual is reversed, not deleted.

New salary revisions start on the first of a payroll month and append in date order. Payroll selects the recorded version effective for its month. Calculated/paid months stay protected; correct them with reviewed adjustments. A not-yet-used version can be corrected before a protected payroll exists. No missing historic salary versions are fabricated. The existing 26-day divisor and late penalty remain hospital policy requiring review, not a claim of statutory compliance.

The browser example preserves the locked October net **BDT 26,900**, adds a November salary revision, an approved BDT 500 earning and BDT 80 staff meal, calculates **BDT 30,420**, then adds an approved BDT 200 deduction and recalculates **BDT 30,220** before independent approval/payment/locking. The October item and its loan recovery remain unchanged.

## Dietary coordination

- Link diet orders to the actual active admission through the patient/admission selector. Free-text admission labels are descriptive, not encounter links.
- Pending diets requiring approval cannot generate food. A pending or active NPO instruction holds other oral diets for that patient during the instruction interval. It also cancels affected undelivered tickets, including overdue meals when the hold is already effective.
- An approved replacement diet ends the prior matching patient/encounter/meal-type interval at the new start and cancels superseded undelivered tickets. Future-dated replacements preserve the preceding interval.
- Editing a diet renews required approval and cancels old undelivered tickets. Cancelled tickets can be replaced after review; delivered history is retained. The dietitian can explicitly stop/cancel an order from **Edit diet**. Stopping one NPO instruction does not bypass another active hold.
- Delivery rechecks current diet/admission eligibility. NPO is not an allergy override; it cannot be waived through the kitchen exception field. Only the dietary approver can record an allergy/restriction exception; kitchen roles cannot grant it to themselves.
- Completing IPD discharge stops linked dietary orders and cancels undelivered linked meals in the same transaction. Closed admissions cannot generate new linked food. The connected browser journey verifies this through the doctor's actual discharge workflow.
- Delivered billable inpatient meals use interim invoices. The final bill carries their remaining charges and existing receipts/returns without accruing or collecting the same amount again. Additional billable delivery is blocked after a final admission bill until that bill is reviewed.

## Roles, GUI and reproduction

The connected suite uses normal password logins for HR manager, payroll officer, department head, employee, transport manager, driver, dietitian, kitchen, catering manager, cashier, inventory manager, accountant, doctor, nurse and patient. There is no admin fallback. Operational writes use GUI controls; API reads assert persistence and deliberate forbidden probes assert role boundaries.

New controls include the stock-item editor, stock recipe selectors, fixed-fare dialog, payroll adjustment/review/recalculation controls, admission-linked diet editor, order stop/cancel, meal cancellation, posting history and staff deduction state. Financial amount inputs allow cents. Financial reasons do not receive unrelated clinical snippets. Financial/stock caches are invalidated after the relevant mutations. Responsive dialogs, mobile/tablet pages and persisted figures are checked by the browser suites.

```sh
npm run test:erp:api
CHROME_BIN='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' npm --prefix frontend test -- --watch=false --browsers=ChromeHeadless
npm run test:posting:browser
```

Migrate first with `cd backend && .venv/bin/alembic upgrade head`. Operational migration `20261101_0074` creates posting links, salary revisions/adjustments, recipe store/stock links and payroll snapshots. Its downgrade deliberately refuses to discard posting history. Current head is `20261101_0075`, which preserves the independent payment-provider/reference migration.

The fixture enforces a local development/test database, creates a fresh synthetic branch and tagged resources, and stores credentials only in `/tmp/hms-support-fixtures.json` with mode 0600. It does not alter existing hospital orders, employees or stock. Do not print/copy credentials. No audit/financial test records are silently deleted after a run.

For separate evidence directories:

```sh
HMS_FOUNDATION_OUTPUT_DIR=/tmp/hms-posting-fresh-foundation HMS_POSTING_OUTPUT_DIR=/tmp/hms-posting-fresh-final npm run test:posting:browser
```

A deliberate `HMS_E2E_RESUME=1` is for debugging the existing fixture, not fresh acceptance. Keep resumed evidence separate from the final fresh run. Do not run a frontend build during browser acceptance because it rewrites runtime configuration.

## Legacy and remaining acceptance boundaries

Stock-use reports honor the selected meal date/ward/type filters and include linked physical issues only; cancelled planned recipes are marked not issued and do not inflate consumption.

Migration does **not** post historic money/stock, charge old meals again, invent opening balances or deduct historical staff-meal review flags. Old catering tasks/trips remain `manual_review`; old staff-meal flags are excluded from automatic payroll. A legacy approved payroll without a verified accrual cannot be marked paid through the new automatic path. A final bill carrying unverified legacy accruals receives a review-required source record rather than invented revenue. A guided legacy reconciliation/import UI remains work for independent review.

Still requiring hospital/Claude acceptance:

- Opening balances, default chart mapping, goods-received/vehicle-payable settlement and matching vendor invoices; live bank/card/mobile-wallet execution; funding controls, payroll payout proof and tax/PF remittance. Recording an event in the book is not execution or confirmation by an external payment provider.
- Counter-cash staff meals, multi-item kitchen BOMs, patient package inclusion, multi-currency and period-close policies. Paid staff-meal eligibility is not itself a cash receipt; automatic recovery here is the explicit payroll path.
- Half-day/partial-month payroll policy, arrears proration, reversals after paid payroll, adjustments to future versions already booked, and legacy salary reconstruction. Do not reopen paid snapshots to bypass the correction workflow.
- Full ER transfer/disposition dietary acceptance, conflicting future orders, prolonged clinical outages, complex admission transfers and concurrent multi-workstation workload. IPD discharge/NPO/replacement behavior is exercised; this does not certify all clinical policy.
- Physical printers/scanners, complete print outputs, very large histories, screen readers and offline/session recovery during these specific write workflows. The barcode/device boundaries in earlier handoff sections remain open.

## Final verification — 2026-11-01

- Backend: **175 passed**, 31 existing serializer/deprecation warnings; `/tmp/hms-posting-verified-api-tests.log`.
- Frontend: **45 passed**; `/tmp/hms-posting-final-frontend-tests.log`. Build passed; `/tmp/hms-posting-final-build.log` (existing JsBarcode CommonJS advisory).
- Fresh role-owned browser acceptance: **208 stages** across both connected suites, **15 roles**, **68 GUI checks**, zero JavaScript/unexpected API errors. Fixture `ae0d2b3a9`; `/tmp/hms-posting-release-foundation/report.json` (108 stages), `/tmp/hms-posting-release-final/report.json` (100 stages), `/tmp/hms-posting-release-browser.log`.
- The final read-filter correction has separate browser acceptance: **two stock-report checks** verify two actually issued units on the correct date and zero consumption on the unissued/cancelled day. `/tmp/hms-posting-stock-report-check.json` and `/tmp/hms-posting-stock-report-check.log`. This is read-only follow-up after the fresh write journeys; the final backend suite includes its date/ward regression.
- Runtime: `/health/ready` returns 200 and the local frontend returns 200. Latest API log `/tmp/hms-posting-verified-server.log`; frontend `/tmp/hms-posting-final-frontend.log`. Current migration head `20261101_0075` is applied.
