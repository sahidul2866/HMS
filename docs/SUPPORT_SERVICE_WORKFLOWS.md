# HR/payroll, transport and catering acceptance

Use local synthetic data. This guide describes the implemented controls and the remaining integration boundaries; it is not a production payroll or dietary policy certification.

## Roles and workflow

| Area | Actors | Verified path |
| --- | --- | --- |
| Workforce | HR manager, employee, department head | Create an employee, link a branch login, mark department attendance, request own leave, independently approve leave |
| Payroll | Payroll officer, HR manager | Configure salary components and effective date, record a loan and overtime, independently approve overtime, calculate, independently approve, mark paid, lock, reload payslip and loan balance |
| Transport | Transport manager, assigned driver | Create vehicle and HR-linked driver, create patient request, dispatch, start, arrive at pickup, pick up passenger, transit, arrive at destination, complete, record fuel, schedule and complete maintenance |
| Catering | Catering manager, dietitian, kitchen staff | Configure a meal plan, order and approve diet, generate dated meal tickets, prepare, mark ready, send out, confirm delivery, order/issue/serve staff meals |

Migration `20261101_0073` adds `TRANSPORT_MANAGER`, `TRANSPORT_DRIVER`, `CATERING_MANAGER`, and the existing payroll approval permission to HR managers. It preserves independently administered permissions. Driver login ownership follows `transport_driver.employee_id → hr_employee.user_id`; without that link the driver has no assigned trips. HR account options contain only branch login identity fields. Linking an account copies its department when no employee department was supplied. Existing employees can be edited to link the correct account. Never invent links for legacy records.

Leave-policy creation requires HR settings permission. Employee self-service lists only their employee record and associated leave/documents. Department heads see their department; HR/payroll managers see the branch. A transport manager receives a staff directory with salary, bank, national/passport and tax identifiers redacted. Unrelated actors cannot write payroll, dispatch vehicles, alter diets or approve kitchen safety exceptions.

## Payroll behavior

- New salary forms start at zero; all salary components are visible. There are no hidden preset allowances. Use the effective date intentionally. A salary effective after the selected month and an employee joining after that month are excluded.
- Leave requests use inclusive calendar days and cannot overlap an existing pending/approved request. Approval must come from another user. Approved paid leave is not deducted; unpaid leave is clipped to the payroll month and date sets are deduplicated.
- The existing basic-salary/26 day divisor and quarter-day late penalty remain. These are application policy, not a declaration of statutory compliance. Confirm the hospital's workday, attendance, leave, overtime, tax and provident-fund rules before use.
- Loan calculation caps each installment at its remaining balance and honors its deduction start month. Payment updates balances once; repeated paid status is idempotent. Changed balances must be reviewed before payment.
- Whole-branch/department overlap and repeat employee-month payroll are blocked. Branch calculations are serialized. Empty and negative-net calculations are rejected.
- The calculator cannot review/approve their own payroll. The same restriction applies to overtime approval. Only approved overtime contributes to salary. Paid payroll cannot be reopened through status changes. Approval attribution survives payment/locking.
- The browser acceptance example records 26,000 basic + 2,000 allowance + 200 approved overtime − 1,000 unpaid leave − 300 loan = **BDT 26,900**. Loan balance becomes zero; approved, paid and locked state persists after reload.

## Transport behavior

Request/vehicle/driver/trip mutations check branch ownership. Vehicle and driver assignment locks prevent concurrent double booking. Override reasons cannot bypass an existing active trip or create another trip for an assigned request. Closed trips cannot restart. Drivers only list/update their own assigned trips; completion and cancellation require their corresponding action permission, while charge/status changes require transport billing permission.

The GUI exposes the next trip stage. Completing a trip releases the vehicle and driver. Active vehicles cannot enter maintenance. Scheduled/in-progress maintenance holds a vehicle; completing the last open maintenance record makes it available again. A completed maintenance entry can also be recorded explicitly. Fuel and maintenance actions have persistent audit records; audit serialization handles linked UUIDs and dates. The driver-trip report now lists actual trips.

## Catering behavior

Patient, admission and ER references must agree on patient/branch. Approval-required diets cannot be downgraded by the create payload. Meal plans must match the diet/branch. Editing a diet cancels undelivered old tickets and requires fresh review when the diet requires approval. NPO does not generate meals. Pending diets do not generate meals.

Generation locks the branch, checks each scheduled serving instant against the diet's start/end, uses Asia/Dhaka serving time, and skips existing diet/date/type tickets. Meal, staff-meal and inventory-usage reads and status changes are branch scoped. Preparation and delivery follow ordered stages. A delivery actor cannot prepare; kitchen staff cannot authorize a safety override. A diet approver may document a meal safety exception through the kitchen queue before authorized kitchen staff proceed. Closed meals cannot reopen. A staff meal follows ordered → issued → served, with cancellation before serving.

## Reproduce

With API and frontend running and migrations current:

```sh
npm run test:erp:api
CHROME_BIN='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' npm --prefix frontend test -- --watch=false --browsers=ChromeHeadless
npm run test:support:browser
```

The browser fixture enforces localhost and a development/test database, creates a new synthetic branch, nine ordinary password-login role accounts, a patient and an unpaid-leave policy. Operational writes use browser controls. Read-only API assertions verify persisted totals and actor scope; intentional forbidden API probes must return 403. Credentials are written only to `/tmp/hms-support-fixtures.json` with mode 0600; never copy them into this repository or handoff.

The final fresh evidence is `/tmp/hms-support-fresh-final/report.json` (102 stages, nine roles, no unexpected API/JavaScript errors), its state file and screenshots. It includes 38 page/dialog/filter checks at mobile/tablet sizes. Backend: 138 passed; frontend: 45 passed; build passed. Additional runtime login/read checks are recorded in `/tmp/hms-support-runtime-readcheck.json`. By default new runs write `/tmp/hms-support-browser/report.json`; set `HMS_E2E_OUTPUT_DIR` for a separate evidence directory. `HMS_E2E_RESUME=1 node frontend/e2e/support-workflows.cjs` explicitly resumes the current fixture; normal execution starts from the beginning. Use the npm command for a fresh fixture. Keep failure/resume evidence separate from the final fresh run. Do not run a frontend build during a browser journey; it rewrites runtime configuration. A stale Angular compilation-error overlay may require restarting the development server after fixing the compilation error.

## Still requiring work and independent review

1. **Financial/stock integrations:** catering billable meal amounts, kitchen inventory usage, transport charges and staff-meal payroll-review flags remain operational records. They do not automatically issue physical stock, post cashier invoices/GL entries, pay banks, or deduct staff meals from a payroll item. The staff-meal UI explicitly labels its flag for payroll review. Design atomic posting/reversal, reconciliation and legacy-data migration before enabling automatic money/stock changes.
2. **Salary/attendance corrections:** a salary associated with paid/locked payroll remains protected. Future salary revisions, retroactive adjustments, partial-month proration, half-day leave, arrears, attendance corrections after calculation, loan rescheduling and statutory policy need a dedicated adjustment/version workflow and further acceptance tests. Do not unlock paid history to bypass this boundary.
3. **Broader HR paths:** recruitment, performance, exits, file storage/secure document downloads and biometric/time-clock imports were not exercised as complete role-owned write journeys in this continuation. Their presence in navigation does not establish complete acceptance.
4. **Transport operations:** real GPS/maps, emergency dispatch policy, planned reservations versus live trips, robust breakdown/incident recovery, vehicle/driver reassignment and advanced filtered/export reports need independent acceptance. Test simultaneous dispatch under real workstation load. Identity strings on fleet and meal records are not physical printer/scanner acceptance.
5. **Dietary operations:** nutrition/allergen rules, changed/NPO diet coordination, multiple concurrent diets, admission discharge/cancellation integration, food inventory costing, cutoff policy, delayed/refused/redelivery scenarios and real patient receipt verification require hospital review. Do not use a synthetic override as evidence of clinical suitability.
6. **GUI resilience:** mobile/tablet and selected expanded dialogs are checked by this suite; offline/session recovery, very large directories/queues, keyboard/screen-reader behavior, print layouts and physical barcode/label devices still need targeted review. Preserve typed work and verify retries never duplicate financial or clinical actions.
