# OPD financial billing delivery — 19 November 2026

## Implemented behavior

The existing FastAPI/SQLAlchemy billing and Angular billing screens were extended. Existing invoice, payment, return, OPD, worklist and accounting integrations remain the application paths.

- Versioned, effective-dated hospital/branch, department, category, doctor, referrer and item financial policies. A policy save appends a version; it does not edit earlier rules.
- Item and invoice percentage/fixed discounts, defaults, combined caps, discount prohibitions, role restrictions and administrator approval. Existing catalog caps now apply to the combined item and allocated invoice discount. An invoice-level concession cannot bypass a service restriction.
- Separate hospital, doctor and external participant discount responsibility. Responsibility shares and commission participant shares independently total exactly 100%.
- Consultation doctor revenue percentages or fixed hospital deductions, doctor-funded concessions, approved individual fee overrides and authorized zero-price consultations. Configured zero doctor fees no longer receive invented fallback prices.
- Disabled/enabled commissions, gross/net basis, fixed/percentage commission, absolute limits, multiple participants and pending commissions. Disabling an arrangement in a new policy affects future invoices; historical transactions retain their rules.
- Append-only participant revenue, commission, discount, approval, settlement and reversal entries. Reversals after settlement create recoverable balances; pending negative adjustments reduce future available settlements.
- Existing partial payments and mixed payment methods, plus policy-authorized advance collections against an invoice. BDT calculations use Decimal and half-up rounding; new discount allocations use a deterministic largest-remainder method to distribute every paisa exactly.
- Atomic full cancellation and refund, partial item/quantity returns, retained original invoices, cumulative partial-credit rounding, payment/refund history, original clinical records and participant allocation adjustments.
- Frozen consultation cancellation, whole-package/quantity cancellation and started-service cancellation controls. Started clinical service cancellation requires the explicit frozen policy and billing administration permission. Physical medicine receipt restrictions remain enforced.
- Idempotency keys and serialized payment, refund, return, cancellation and settlement commands. The API rejects reuse of a key with conflicting payment/refund details.
- Backend invoice preview now supplies the creation screen's totals and validates financial policy limits. OPD consultation totals use the same allocated line amounts as invoices/returns; the previous double subtraction of item discounts was fixed.
- Invoice printing supports frozen discount visibility, hospital name/address/contact, quantities, discounts, current net payable after credits, refunds, paid and due amounts. Browser-generated PDF output was exercised in the real browser test.
- Registered external doctor, pharmacy, individual, agent, organization and other referral sources, with selection on the invoice creation screen.
- Billing Settings includes a versioned policy editor, referral registration, participant ledger and settlement entry. The invoice detail menu includes Cancel and refund invoice.
- Accounting journal identifiers now retain a complete UUID. Testing exposed collisions in the old four-character UUID suffix; manual second-only identifiers were also corrected.

## Configuration

Open **Billing → Settings → Financial policies and settlements**. Existing global and item catalog controls remain on that page. Financial rules use a validated JSON editor, with decimal amounts represented as strings. Copy an existing policy to create its next version.

Precedence, from highest to lowest: **item → referrer → doctor → category → department → hospital**. At the same scope, a branch version takes precedence over a hospital version; newer applicable effective dates/versions win. Each policy is a complete rule set, rather than a partial merge. Department matching uses the service category's department, including mixed invoices. Legacy item catalog caps remain hard bounds.

Selectors:

| Scope | Selector |
| --- | --- |
| hospital | `*` |
| department | Department name |
| category | Billing type UUID |
| item | Billing catalog configuration UUID |
| doctor | Consulting doctor user UUID (or internal referral user without an OPD visit) |
| referrer | Registered external referral UUID |

Main rule fields:

| Area | Fields |
| --- | --- |
| Discounts | `discounts_allowed`, `default_discount_percentage`, `max_percentage`, `max_amount`, `combine`, `approval_required`, `allowed_roles`, `override_roles` |
| Responsibility | `discount_sharing` keyed by `hospital`, the doctor account, or configured participant account keys |
| Consultation | `doctor_key`, `doctor_revenue_percentage`, `hospital_fixed_deduction` |
| Commission | `commission_enabled`, `commission_basis`, `commission_percentage` or `commission_fixed`, `commission_limit`, `commission_approval_required`, `participants` |
| Cancellation/refund | `refund_approval_required`, `consultation_cancellable`, `allow_started_cancellation`, `package_cancellation` (`whole`/`quantity`) |
| Collections | `allow_advance_payments` |
| Printing | `show_item_discounts`, `hospital_name`, `hospital_address`, `hospital_contact` |

Use persistent recipient account keys consistently across policies. Participant entries retain name/type/share in the immutable policy version. Doctor revenue and referral commission are different components and may use different accounts. A policy requiring approval is applied by a user with existing `billing.service.manage`; allowed/override roles use role codes. Discount override roles can override policy maxima, but cannot bypass discount prohibitions or catalog hard caps.

For the BDT 800 consultation / 70% doctor / BDT 100 doctor-funded discount example:

```json
{
  "doctor_key": "doctor:ACTUAL_USER_UUID",
  "doctor_revenue_percentage": "70",
  "discount_sharing": {"doctor:ACTUAL_USER_UUID": "100"}
}
```

Apply a BDT 100 item discount or approved invoice discount. The persisted allocation is doctor gross revenue 560, doctor discount responsibility -100, hospital revenue 240, and patient payable 700.

Settlement rows record paid-out money; they do not initiate a bank or mobile-wallet transfer. Approval transfers are append-only. Negative net balances represent recovery amounts, not a rewrite of past payouts.

## APIs

Existing billing APIs remain. Additions:

- `GET/POST /api/v1/billing/policies`
- `GET /api/v1/billing/allocations`
- `POST /api/v1/billing/settlements`
- `GET/POST /api/v1/billing/referrers`
- `POST /api/v1/billing/invoices/{id}/cancel`

Payment, refund, return and cancellation bodies accept an optional `request_key`. Existing callers remain compatible; new callers should supply a stable key per financial operation. Settlement requires a key. Payment bodies accept `advance: true` only where the frozen policy allows it. Item bodies accept `unit_price_override` plus `override_reason`, restricted to billing administrators.

## Migration and data preservation

Migration: `backend/alembic/versions/20261119_0076_billing_policies.py`, after `20261101_0075`.

Adds:

- `billing_policies`
- `billing_allocations`
- `billing_commands`
- `billing_invoice_items.financial_snapshot`
- `referred_doctors.referrer_type`, with a backward-compatible external-doctor default
- PostgreSQL mutation-rejection triggers for policies, allocations, financial commands and billing events

Migration upgrade, mutation rejection and downgrade were executed against an isolated PostgreSQL schema. No development or production migration was applied. Historical invoices are not automatically recalculated or backfilled with newly invented participant obligations. Existing records without frozen allocations retain the legacy allocation method; new invoices freeze their exact per-line invoice discount allocation.

## Test coverage and execution

New backend cases include all seven responsibility patterns, multiple commission participants and gross/net bases, invalid sharing/limits, rounding across hundreds of allocation recipients, authorization, partial payments/returns, settlement recovery, historical policies, duplicate/concurrent commands, full cancellation at different payment levels, advances, package restrictions, fee overrides/free consultations, precision boundaries, mixed departments, API workflows and migration rollback/immutability.

New frontend cases cover policy JSON validation, effective dates, exact decimal request values, settlement retry keys, copying policy history, visible/hidden invoice discounts, quantities, branding escaping and refunded/current payable printing.

The real browser test uses the built Angular app, a local HTTP API with startup bootstrap disabled, and a fresh PostgreSQL schema. It saves policy configuration, verifies the persisted policy, opens a historical paid invoice, checks discount visibility, generates its PDF, cancels/refunds through the actual screen, and verifies persisted cancellation/refund balances. Existing API integration tests cover patient registration, appointments, OPD consultation/orders, invoicing/payments and clinical workflow preservation.

Execution commands (from repository root):

```sh
HMS_TEST_DATABASE_URL=postgresql+psycopg://localhost/hms_erp_test HMS_RUN_BROWSER_TESTS=1 PYTHONPATH=backend backend/.venv/bin/pytest backend/tests -q
cd frontend
CHROME_BIN='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' npm test -- --watch=false --browsers=ChromeHeadless
npm run build
```

Verification results:

| Check | Passed | Failed | Skipped |
| --- | ---: | ---: | ---: |
| Full backend suite (PostgreSQL, APIs, concurrency, migration, real browser) | 265 | 0 | 0 |
| Frontend ChromeHeadless suite | 59 | 0 | 0 |
| Angular production build | Successful | 0 | 0 |

83 backend cases and 6 frontend cases were added. The final browser check asserts exactly two invoice PDF pages (one patient copy and one office copy). Both PDF pages were also rendered with the available PyMuPDF installation and visually inspected; text extraction checked the payable, discount and refund labels. Print CSS was corrected to prevent the screen's responsive layout from expanding the invoice to four pages.

Expected warnings remain: existing Pydantic/passlib/websocket deprecations, serializer warnings in older tests, cyclic metadata ordering in migration-test setup, and the existing jsbarcode CommonJS build warning. None caused a failed check.

Logs: `/tmp/hms-billing-delivery-final.log`, `/tmp/hms-final-frontend-tests.log`, `/tmp/hms-final-frontend-build.log`. Browser artifacts: `/tmp/hms-billing-policy-browser.png`, `/tmp/hms-billing-invoice.pdf`.

The existing billing-operations fixture cap was increased from 20% to 50% so its amendment/history test continues exercising permitted combined discounts; dedicated new tests verify that combined discounts exceeding catalog limits are rejected.

## Boundaries and remaining limitations

- Financial policy editing currently uses validated JSON rather than dedicated inputs for every rule. The administration workflow is functional, but a fully guided policy builder remains additional UI work.
- Approval means an authorized administrator performs the operation. There is no separate maker/checker approval inbox or remote approver workflow.
- Printing supports branding and discount visibility in the existing invoice layout. Arbitrary template layout design and a server-side PDF service are not implemented; PDF output uses browser printing.
- Advance collections are invoice-linked. A new standalone patient wallet/advance account was not introduced.
- Package restrictions operate on a billed package/quantity line. There is no new package-component pricing engine or component-level package refund editor.
- Existing IPD carry-forward money/charge behavior is regression-tested, but transfer/reversal of the new participant ledger across interim-to-final IPD consolidation is not implemented. Do not enable new participant policies for that lifecycle without extending and testing that transfer first.
- Browser coverage exercises administration, invoice print/PDF and full cancellation. The entire registration-to-settlement plus partial-return journey is covered through application/API/database tests, not one uninterrupted browser script.
- Bank/mobile-wallet disbursements, physical printer hardware and organization-specific legal approval of referral arrangements were not exercised. Commission arrangements can be disabled by policy.

These limits mean this change should not be described as completion of every production requirement in the original brief. No production deployment or financial-record modification was performed.

## Changed file manifest

Backend:

- `backend/alembic/versions/20261119_0076_billing_policies.py`
- `backend/app/models/__init__.py`
- `backend/app/models/billing.py`
- `backend/app/models/billing_policy.py`
- `backend/app/modules/accounting/service.py`
- `backend/app/modules/billing/idempotency.py`
- `backend/app/modules/billing/operations.py`
- `backend/app/modules/billing/policies.py`
- `backend/app/modules/billing/return_fulfilment.py`
- `backend/app/modules/billing/router.py`
- `backend/app/modules/billing/service.py`
- `backend/app/schemas/billing.py`
- `backend/app/schemas/billing_policy.py`
- `backend/app/utils/billing_amounts.py`
- `backend/tests/test_billing_operations.py`
- `backend/tests/test_billing_policies.py`
- `backend/tests/test_billing_policy_browser.py`

Frontend:

- `frontend/src/app/features/billing/models/billing.models.ts`
- `frontend/src/app/features/billing/pages/billing-create/billing-create.component.html`
- `frontend/src/app/features/billing/pages/billing-create/billing-create.component.ts`
- `frontend/src/app/features/billing/pages/billing-desk/billing-desk.component.html`
- `frontend/src/app/features/billing/pages/billing-desk/billing-desk.component.ts`
- `frontend/src/app/features/billing/pages/billing-settings/billing-settings.component.html`
- `frontend/src/app/features/billing/pages/billing-settings/billing-settings.component.ts`
- `frontend/src/app/features/billing/pages/billing-settings/financial-policies.component.ts`
- `frontend/src/app/features/billing/services/billing.service.ts`
- `frontend/src/app/testing/billing-policies.spec.ts`

Documentation: `docs/OPD_FINANCIAL_BILLING_DELIVERY.md`.
