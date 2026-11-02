# Hospital ERP GUI cleanup goal

Status: **in progress**. The built-in tracker reached `usageLimited`; work and remaining acceptance criteria are tracked here. The whole-app goal is not complete.

Objective: make the whole ERP readable, aligned and easy to operate, starting with the cluttered OPD/billing workflows. This is a visual and interaction review, not just a successful build or an overflow scan.

## Acceptance criteria

- Each screen has a clear main task and primary action. Large workflows reveal patient, work-item and payment/review steps separately when appropriate.
- Advanced filters, discounts, classification, history and internal settings remain available without dominating the main task.
- Real populated rows stay aligned. References do not wrap into broken fragments; amounts and statuses remain readable. Smaller screens get a deliberate layout or contained table scrolling.
- Primary controls remain visible without floating widgets or toasts obscuring them. Dialogs have predictable close/focus behavior.
- Back/forward step navigation preserves entered work. Moving between steps does not submit a financial transaction.
- Loading, empty, validation, permission, error and success states explain the next action.
- Review at **390, 768, 1024 and 1440px**, including long names, identifiers, multiple items, actual records and expanded details—not only empty pages.
- Workflow checks must still exercise booking, payment, prescription and IPD handoffs after changes.

## Module coverage

| Area | Current status | Next evidence required |
|---|---|---|
| Billing entry / OPD payment | Patient → Items → Payment; populated rows and draft navigation passed at four widths; posting exercised in hospital journey | Dedicated long catalog-name and discount validation review |
| Billing invoice list | Six main columns; optional filters/export; four-width populated list and detail access verified | Keyboard and restricted-role review |
| OPD visit list | Six grouped columns; four-width populated review and consultation journey passed | Restricted doctor/reception role review |
| OPD consultation / queue | Queue/report tables contained; filter grid compact; screenshot review and calling/prescription journey | Expanded prescription editor and PA configuration review across roles |
| IPD | Static four-width routes plus 16-stage connected hospital journey, including mobile care, transfer and discharge | Broader care/settings dialog combinations and keyboard review |
| Registration / appointment | Four-width static routes; populated registration/booking/check-in exercised in hospital journey | Search edge cases and keyboard/focus review |
| Laboratory / radiology / PACS | Four-width static routes; department integration covered by backend suite | Expanded result/report dialogs and actual image-viewer review |
| Pharmacy / inventory | Static route sweep; inventory grids and currency charts fixed | Expanded dispensing, purchase and stock dialogs |
| Accounting / billing operations / reports | Billing operations split into reports, cash handover and setup; native money tables; other static routes swept | Expanded accounting forms and multi-user handover review |
| Emergency / OT / blood bank | Static route sweep; blood-bank filters collapsed and responsive grids fixed | Intake/OT dialogs and expanded screening forms |
| HR / transport / telemedicine | Static route sweep; HR mobile metric collision and currency sizing fixed | Expanded dispatch, payroll and teleconsultation flows |
| Patient portal / profile / notifications | Static route sweep; portal heading and recoverable empty/error state added | Actual patient-account workflow, document and booking dialogs |
| Administration / configuration | Role selector, searchable collapsed permission modules, optional scopes; AI configuration disclosures | Save/reload permissions with restricted accounts; expanded configuration dialogs |
| Shared navigation / tables / dialogs | Native table layout and grid containment; assistant launcher moved beside tabs; invalid hidden fields open their section | Keyboard/focus audit and broader dialog adoption |

Do not mark this whole-app goal complete because the first billing/OPD pass succeeds. Update the matrix with screenshots, checks and remaining defects as each area is reviewed.

## First-pass design changes

Billing opens at item editing when a patient/visit is already selected. Otherwise staff select or register the patient first. Item editing has stable service/quantity/amount/remove columns and optional per-item discounts. Suggested services are collapsed. Payment has one leading total, an item review and an expandable amount breakdown; discounts/classification and referral/internal notes are optional disclosures. Posting appears only at payment.

OPD and invoice lists group related data rather than presenting a separate column for every property. Long reference strings use an accessible full-value title and remain on one line. Native table layout is kept inside a scrolling boundary. Full information remains available in record detail and print views.

## Commands and artifacts

```sh
npm run test:gui:billing
npm run test:gui:inventory
npm run test:ipd:browser
npm run test:erp:ui
CI=true npm --prefix frontend run build
```

`test:gui:billing` edits temporary browser forms but never posts invoices/payments. It checks populated billing rows and navigation between item/payment steps, then reviews OPD/invoice lists at four widths. Screenshots and JSON: `/tmp/hms-billing-layout/`.

The connected browser journey posts synthetic local records, as described in `IPD_MODULE.md`. API/JS errors and visual/geometry failures must be fixed or recorded; inspect screenshots in addition to automated assertions.

## Whole-app route sweep and follow-up fixes

The read-only static menu inventory covers **139 routes**. Initial desktop (1440px) and mobile (390px) sweeps completed; flagged pages were inspected and fixed. A subsequent **32 checks** (eight affected routes × 390/768/1024/1440px) completed without overflow, density, missing-heading or captured API/JavaScript flags. The full tablet sweep also completed (**278 route/viewport pairs** at 768/1024px), with nine flags tracing to the same OT case-sheet action grid at 1024px and no captured API/JavaScript errors. That grid was changed to fit its action labels and is included in final targeted rechecks. A route sweep is triage evidence: it does not cover every dialog, permission variant, error or populated workflow.

Confirmed and fixed defects included: outpatient reports expanding the content to 2705px; blood-bank filter grids exceeding their container; hundreds of always-visible role permission checkboxes; inventory currency glyphs overflowing a fixed count column; a global danger-button style laying out the HR Absent tile horizontally; long catering configuration values overflowing mobile cards; and the OT case action grid exceeding its tablet container. Small selects no longer get redundant search inputs; asynchronously loaded large catalogs still gain search. Field validation opens collapsed ancestor sections before focusing the correction. Two regression tests cover these behaviors.

The assistant launcher now occupies a normal row beside open-page tabs, rather than covering patient actions or financial values. Its panel opens only on request. Billing Operations has separate financial report, cash handover and type/department views; entered form values remain in component state when switching views.

Artifacts are machine-local, under `/tmp/hms-gui-inventory`, `/tmp/hms-gui-mobile`, `/tmp/hms-gui-final-recheck`, `/tmp/hms-gui-tablet`, `/tmp/hms-billing-layout` and `/tmp/hms-ipd-browser`. Use the reusable scripts to reproduce them. The inventory reports flags for manual inspection and intentionally does not treat an unflagged page as complete GUI certification.

The mobile/tablet header now keeps scanner, notifications and account access visible, with display density, theme and manual available inside the account menu. Collapsed quick-action groups share a row on narrow screens. The account menu scrolls on short screens. The billing layout regression checks verify a compact header and continued access to these settings.

## Remaining acceptance work

- Review expanded clinical/settings dialogs, especially prescription editing, IPD care/settings, OT case actions, dispensing and accounting forms. The static sweep does not open every dialog.
- Repeat relevant flows as doctor, reception, cashier, supervisor and patient accounts; the menu sweep uses the local superadmin account.
- Exercise keyboard-only navigation, dialog focus return, long localized labels and validation/error states across remaining modules.
- Judge screenshots and workflows manually; contained scrolling and a clear heading alone do not establish good usability.

Do not mark the entire GUI objective complete based on the static sweep. The backend suite's existing expected failure for unpaid-invoice returns is recorded in `INDEPENDENT_REVIEW.md` and should remain visible during the broader ecosystem review.

## Latest verification for this continuation

- Production frontend build passed; existing JsBarcode CommonJS optimization advisory remains.
- Backend regression suite: **62 passed, 1 existing expected failure**.
- Billing/OPD layouts, invoice panels, Operations views, assistant launch and mobile header/settings access: **16 checks passed**, covering 390/768/1024/1440px.
- Connected hospital browser journey: **16 stages passed**, zero captured API/JavaScript errors.
- Full static route sweeps: **139 routes × four widths = 556 route/viewport pairs** across the desktop, mobile and tablet runs. Initial flags drove the fixes above; these were not all runs against one final build.
- Final targeted sweep against the latest build: **68 route/viewport pairs**, covering all affected modules and OT case-sheet subroutes, zero flags or captured API/JavaScript errors. Artifacts: `/tmp/hms-gui-release-recheck`.
- `git diff --check` passed.

Frontend regression suite: **30 passed** on the final source (`/tmp/hms-gui-tests.log`); screenshots and the remaining acceptance matrix should accompany any independent assessment.


## Ecosystem continuation — 2026-11-01

See the newest section of `CLAUDE_HANDOFF.md` for verified results and outstanding work. This continuation restored hidden primary header actions; added named dialogs with keyboard/focus behavior to OT, HR, transport and catering; fixed the catering backdrop intercepting controls; added persistent transport form labels; collapsed pharmacy creation and hid unauthorized catalog actions; connected exact product/batch barcode routes; and switched 63 feature screens to lazy loading. Billing credits now explain net payable separately from the original charge and actual cash payout.

The broader GUI/ecosystem objective remains unfinished. Static route coverage and sampled dialog geometry do not prove every expanded workflow, staff role, error state or external device works.

## Core-role write acceptance and stock reviews — 2026-11-01

Reception branch-scoped visit access is repaired. Cashier OPD/IPD billing uses financial drafts without forbidden clinical reads. Stock reconciliation/historical allocation/disposal are split into dedicated tabs with independent review and audit details. Billing evidence forms no longer show unrelated clinical suggestion chips; long user identity text no longer pushes desktop account controls outside the viewport.

The fresh seven-role browser journey passed 41 stages with zero captured API/JavaScript errors, covering actual owned writes through patient registration, OPD, pharmacy return, stock review/disposal sign-off, IPD, final billing/discharge, cash custody and patient self-service. This replaces the earlier five-role navigation-only limitation for these specific workflows. Specialist module/role browser acceptance and broad scale/error/device checks remain open; see the latest Claude handoff for the precise boundary.

## Specialist role workflows — 2026-11-01

Lab, radiology, blood bank and OT now have a connected specialist write journey, including patient report release and real OT cashier invoices. Fixed the eight-tab navigation blocker, permission-inappropriate OT actions, clinical confirmation defaults, blood patient/issue UUID entry, oversized checkboxes and raw report JSON. Blood forms have persistent labels; selected OT case panels come first on mobile with searchable, bounded schedules.

Evidence: fresh 85-stage journey across ten accounts with zero captured errors; final read-only follow-up with five case-search checks and 16 responsive panels; 122 backend and 42 frontend tests passed. See the newest Claude handoff section for the exact distinction between fresh writes and the final layout-only run, artifact paths and remaining policy/device/scale/editor acceptance.

### Support-service continuation — 2026-11-01

HR/payroll, transport and catering now have role-owned browser write acceptance plus 38 focused responsive checks (18 pages, 16 dialogs, four expanded filter panels). Removed duplicate HR subpage hero actions; made the payroll summary month/recent runs explicit; corrected payslip spacing; exposed/preserved salary components; collapsed transport/catering filters so mobile work queues remain visible; separated dietary restrictions from allergy alerts; and constrained actions to the actor and workflow stage. Nine-role fresh acceptance passed 102 stages with zero unexpected API/JavaScript errors. See `docs/SUPPORT_SERVICE_WORKFLOWS.md` and the final support-service section in `docs/CLAUDE_HANDOFF.md` for evidence and remaining GUI/integration boundaries. This is focused acceptance, not certification of the entire ERP GUI.

### Automatic posting/correction continuation — 2026-11-01

Added role-owned fare, stock recipe/item, payroll adjustment/review/recalculation and dietary edit/stop/cancel controls. Corrected currency input increments and removed clinical suggestions from financial reasons. Posting and deduction states, separate payslip adjustments and actual stock-use status are visible; cancelled unprepared meals do not masquerade as pending stock issues. The connected acceptance exercises 15 roles, including inventory, cashier, accountant, nurse and patient, with expanded editors at 390/768 px. See `docs/AUTOMATIC_POSTING_WORKFLOWS.md` and the latest Claude handoff for release verification and explicit remaining GUI/device/resilience boundaries.

Final evidence for this continuation: 208 fresh browser stages across 15 roles, including 68 responsive page/dialog/filter checks, plus two focused stock-report checks after the final date-filter correction. All passed with no unexpected API/JavaScript errors; 175 backend tests, 45 frontend tests and the frontend build passed. Final artifacts are `/tmp/hms-posting-release-foundation`, `/tmp/hms-posting-release-final` and `/tmp/hms-posting-stock-report-check.json`. Advanced legacy report widgets and full device/resilience accessibility acceptance remain explicit review items in the Claude handoff.
