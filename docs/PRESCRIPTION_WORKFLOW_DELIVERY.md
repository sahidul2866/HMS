# Prescription workflow delivery — 19 November 2026

## Implemented behavior

The existing Angular OPD editor, configuration workspace, FastAPI OPD services, pharmacy catalog, patient history and billing integration were extended. No separate prescription application or parallel form builder was introduced.

- Assigned doctors can open walk-in and appointment consultations and prescribe independently of consultation payment. Existing doctor-scoped working lists and patient history enforce clinical access. Clinical consultation and prescription status remain separate from financial status.
- Hospital consultation collections use actual billing invoices and receipts. Doctor-direct claims, pending payment, free consultation and waiver information are recorded separately. Free status is rejected on chargeable consultations. Existing partial payments, discounts, outstanding balances, returns and refunds remain in billing; financial reversal does not delete signed clinical records.
- External receipt claims freeze applicable doctor-share configuration or existing invoice financial rules. Claims are idempotent, cannot exceed the remaining consultation amount, and do not produce hospital cash. Authorized finance collectors can append an evidence-based verified/rejected decision and link an actual posted hospital-share remittance receipt. Links validate branch, receipt source/reference, available cash and remaining share, support partial remittances, prevent duplicate links and create no additional cash. Reversed receipts cease counting toward the reconciled balance. Hospital collections are blocked for amounts already covered by active direct-payment claims; finance-rejected claims release that reservation. The original claim and rule snapshot remain immutable. Missing rules are explicitly reported and verification is rejected.
- Drafts support optimistic concurrency, background autosave, session recovery, interrupted-entry recovery, stale-response protection when changing patients, explicit save, preview and keyboard shortcuts (Ctrl/Cmd+S and Ctrl/Cmd+P). Browser tests exposed and drove fixes for start-visit and late-response data loss.
- Finalization requires the active assigned doctor. Signed content, patient, doctor header/BMDC/signature, orders, template payload/version and timestamps are frozen. Amendments create another signed version; earlier signed versions remain intact. Voiding preserves clinical history and prevents subsequent dispensing. Completed clinical intent cannot be silently rewritten; withdrawing an item in an amendment preserves completed care and financial records.
- Immutable clinical events record creation, changes with before/after values, signing, amendment, voiding, payment information and external receipt review. Database triggers reject changes/deletion of revision, template-version, external-claim and event history.
- The existing configuration workspace supports field drag/reorder, required/default/visibility/print visibility, validation, conditional visibility, columns, labels, safe rich-text marks, dates, number/choice controls, catalog selectors, canonical medicine/investigation rows, generic repeating tables, reusable sections, duplicate templates and preview. Standard editor section visibility is independent of print visibility. Template revisions do not change signed documents.
- Templates resolve doctor, department and hospital/branch assignments. Ten editable starters can be installed idempotently: General OPD, Internal Medicine, Pediatrics, Gynecology and Obstetrics, Cardiology, Orthopedics, Dermatology, ENT, Follow-up and Minimal Clinic. They contain no invented medicine or dosing defaults.
- Medicine search reuses the approved existing pharmacy catalog: brand, generic, partial input, strength, dosage form, manufacturer and maintained aliases. One-letter searches work. Approved Bangla aliases are searchable. Token matching supports brand-first and generic-first queries; brand exact/prefix matches rank first. Debounce, stale-response guards and a bounded short-lived query cache reduce requests. Catalog selection never infers dose, frequency, route, timing or duration.
- Structured medicine entries retain the doctor's instructions and explicit catalog identity. Custom dose/frequency text remains available alongside entry shortcuts such as `1+0+1`. Existing ingredient context flags duplicate active ingredients. Allergies and prior context are visible. Favorites, recent/frequent items, advice/snippets and saved combinations reduce typing.
- Investigations use the existing approved investigation catalog and existing clinical order workflow, with duplicate prevention and idempotent batch insertion. A suggestion alone does not create a financial charge. Existing billing workflows control charge creation. Diagnosis suggestions reuse configured diagnosis text and free-text documentation.
- Print preview uses frozen signed content, configurable A4/A5/custom paper, margins, columns, English/Bangla labels, optional hospital name/logo, doctor header, BMDC, signature and medicine tables. Print/Save PDF uses the browser print dialog. Historical, draft, legacy and voided outputs are labeled. Multi-page printing repeats table headings and keeps subsequent advice outside medicine rows.

## Configuration and local database

1. Open **OPD → Configuration → Prescription Builder**. Use **Install prescription templates** to add the ten starting profiles. Select a profile, set its assignment, customize fields/sections/paper, preview and save. Reusable sections are saved within the same configuration service.
2. Configure doctor header, BMDC and an approved PNG/JPEG signature in existing OPD settings. A signature image is a visual signature asset; sign authorization is enforced by the authenticated assigned-doctor account.
3. Maintain medicine brand/generic/strength/manufacturer and approved English/Bangla spelling aliases in Pharmacy. No external medicine reference database was imported.
4. Configure existing doctor-share or billing financial rules before recording doctor-direct receipts. In the visit, record the claim; authorized finance staff can inspect **External payment reconciliation** and record an evidence-based review. For money actually remitted, create the appropriate posted accounting receipt using source module `opd_external_remittance` and source reference equal to the external claim UUID (optionally followed by `:receipt-reference`). Link its journal UUID and amount from the reconciliation panel. Finance chooses the proper contra account under its accounting policy; the linking step never creates a second receipt.
5. Preview and select **Print / Save PDF**. Operating-system printer and PDF destination remain under the user's control.

Migration `20261119_0077_prescription_lifecycle.py` follows billing migration `20261119_0076`. It adds visit/order concurrency and prescription fields, approved search aliases, BMDC/signature fields, profile versions, five prescription-related tables, immutable-history triggers and indexes for doctor worklists, medicine scope and template assignments. Legacy prescribed/completed visits receive preserved snapshots marked `legacy_import`; no signing timestamp or verified electronic signature is invented. Upgrade and downgrade preserve the original clinical fields.

The configured **local** PostgreSQL database `hms_dev` was backed up to `/tmp/hms-dev-before-prescription-20261119.dump` and upgraded from `20261101_0075` through `20261119_0077`. Production was not deployed or migrated. A temporary backup should be moved into the organization's normal protected backup process if it is needed long term.

## Files and modules

New backend implementation:

- `backend/app/models/prescription.py`
- `backend/app/schemas/prescription.py`
- `backend/app/modules/opd/prescriptions.py`
- `backend/app/modules/configuration/prescription_presets.py`
- `backend/alembic/versions/20261119_0077_prescription_lifecycle.py`

Existing backend modules updated: encounter/configuration/pharmacy/user models and schemas; OPD router/service; configuration router/service; patient clinical-history scope; pharmacy prescribing search and dispensing guards; user settings/directory signature access; billing payment-source synchronization. Model exports include the new tables.

New frontend implementation: `frontend/src/app/shared/prescription-fields.component.ts`. Existing OPD models/services/register/settings/visit editor, configuration workspace/service, pharmacy medicines/models/service, authentication user model and shared `opd-prescription-printer.ts` were updated.

New automated coverage:

- `backend/tests/test_prescription_workflow.py`
- `backend/tests/test_prescription_browser.py`
- `frontend/e2e/prescription-workflow.cjs`
- `frontend/src/app/testing/prescription-system.spec.ts`

Existing OPD frontend regressions and the ERP integration signer fixture were updated. Earlier billing changes and their separate report remain in the working tree.

## Executed verification

The final combined backend/browser regression result is recorded below. Tests use isolated PostgreSQL schemas and synthetic clinical/catalog data; no test medicines were inserted into the local working catalog.

- Full combined backend regression with browser tests enabled: **357 passed**, no skipped tests, in 111.66 seconds. The run reported existing deprecation/schema-cycle warnings and an accounting Decimal serialization warning; no test failures.
- Prescription backend suite: **88 passed**. Includes all supported payment-state signing, safe field types, ten presets, template assignment/version preservation, approved search variants, clinical access/signing, draft/order conflicts, duplicate requests, real billing receipts/refunds, finance review/remittance/reversal, prevention of duplicate hospital collection, audit, legacy migration upgrade/downgrade and immutable history.
- Angular tests: **75 passed**. Includes field rendering/conditions, shared clinical rows/catalog selection, frozen printing, independent editor/print sections, session recovery and late-response guards.
- Actual browser/API/PostgreSQL workflows: **5 passed** in the dedicated run: hospital payment with UI-configured template and amendment; doctor-direct claim, finance verification and actual remittance linkage; pending payment and long PDF; follow-up with preserved earlier clinical record; previous billing policy/discount/refund regression.
- Production Angular build: passed. Existing `jsbarcode` CommonJS optimization warning remains.
- Short signed PDF and seven-page long prescription were rendered and visually reviewed, including Unicode and every page of the long table. Review samples: [configured signed prescription](testing/prescription/configured-signed-synthetic.pdf) and [seven-page pending-payment prescription](testing/prescription/long-pending-synthetic.pdf). Both contain synthetic records only.

Commands:

```sh
HMS_TEST_DATABASE_URL=postgresql+psycopg://localhost/hms_erp_test \
HMS_RUN_BROWSER_TESTS=1 PYTHONPATH=backend \
backend/.venv/bin/pytest backend/tests -q

CHROME_BIN='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
npm --prefix frontend test -- --watch=false --browsers=ChromeHeadless

npm --prefix frontend run build
```

The browser fixture overrides authentication only inside its isolated test application, exercises the compiled real Angular frontend, and verifies persisted financial and signed clinical values. Production authentication remains unchanged. The browser tests launch the locally installed Chrome and require the built frontend.

Performance uses 10,000 synthetic medicines on local PostgreSQL, measuring full service search including count and result hydration. Actual timings are in [the performance record](testing/prescription/catalog-performance.json); median **62.63 ms**, maximum **78.58 ms** across four representative queries in the final run. These are local measurements, not a production SLA or slow-network benchmark. Worklist/template/scope indexes, bounded search results, debounce, caching and background save are implemented. Load testing under simultaneous real clinical use remains outstanding.

## Remaining limits and operational boundaries

- External claims, verification and remittance links do **not** automatically settle the patient invoice or transfer money. Actual remittance is first posted through the existing accounting workflow, then linked and reconciled against the frozen hospital share. This preserves separation from patient cash receipts; automated patient receivable reclassification and automatic external invoice settlement are not implemented. Claims reserve their consultation amounts against accidental hospital recollection until finance rejects them.
- No licensed interaction/dose-limit engine or verified allergy-to-ingredient mapping is configured. The UI explicitly reports those checks as unavailable. Duplicate ingredient context and recorded allergies are aids, not clinical clearance. No drug or dose is inferred from a partial query.
- Structured ICD diagnosis reference import/coding is not implemented; diagnosis configuration and free text are supported. Catalog data quality and maintained Bangla/spelling aliases remain the hospital's responsibility.
- PDF delivery uses the browser's Print/Save PDF dialog, rather than a server PDF archive. Physical-printer behavior and every operating-system font installation were not tested. Very long two-column/custom-paper layouts have less coverage than the seven-page single-column case.
- The rich-text control supports restricted text/markdown rather than arbitrary HTML. Signature images and authenticated sign events are not certificate-backed digital signatures or externally verified BMDC credentials.
- Dashboard/working-list access, desktop prescribing and browser flows were exercised; exhaustive tablet/mobile device, slow-network, multi-doctor load and user acceptance testing are still required before a production rollout. Historical data checks covered synthetic migration fixtures and the local upgrade, not a full production dataset audit.

These boundaries mean the requested broader production rollout should not be described as fully complete.
