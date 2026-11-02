# Specialist workflow acceptance

## Laboratory and radiology

Cashiers select the department catalog item, post the invoice and collect payment. Catalogs can contain similarly named custom and department items: use the displayed group/code to select the actual investigation. One department work item is created for the linked order.

The laboratory technician records collection, processing, findings and verification. Radiology records readiness, acquisition/report processing, findings and verification. Entry and verification permissions remain distinct even where the standard seeded department role holds both. A separate-person verification policy is not imposed by the default role template.

Department updates synchronize the linked OPD history and existing IPD diagnostic tasks. Patient portal responses mask preliminary findings; only verified/approved reports are presented as released reports. Verified-result entry is restricted to authorized department reviewers. Existing clinical report amendment/versioning and institution-specific release policies still need review before production acceptance.

## Blood bank

The tested sequence is donor registration → recorded screening → collection with a product-label expiry → verified recorded testing → component preparation → patient request → crossmatch → issue. Transfusion updates and unused-unit returns form separate branches. A returned unused unit can be quarantined/discarded or accepted after recording its inspection/time outside the bank. Completed/started transfusion records block returning the unit as unused. A valid accepted return can subsequently be issued for a new request, retaining each issue in history.

Checks enforce branch ownership, exact unit/request/crossmatch identity, component consistency, recorded expiry/testing state, request quantity, source volume and duplicate issue/return boundaries. Component preparation marks the source as processed so the original whole unit cannot also be issued. Recorded reactive/positive testing cannot be hidden by entering a different negative test. Unit locks protect concurrent issue attempts.

Testing checks the records supplied to this app. Required screening panels, donor eligibility thresholds, clinical compatibility protocols, transport/temperature acceptance, product expiry policies and emergency authorization are hospital policy responsibilities and require specialist validation. The app does not execute a biological crossmatch or verify a physical screening test. Source/product expiry and staff attestations must reflect authentic records.

Read-only reports now use actual collections, issues, transfusions, crossmatches, discards, deferrals and reactive tests, rather than reusing a request list. Date filters use Dhaka day boundaries; grouped stock totals include all matching units, while detailed report output is capped at 500 records. The interface uses labeled fields, readable issued-unit/patient choices and tabular report columns.

## Operation theatre

The tested roles own different steps:

- OT manager: room, schedule, workflow transitions, consumable record and room turnover.
- Surgeon: booking and operative note.
- OT nurse: pre-op checklist and recovery handover.
- Anesthetist: assessment and clearance.
- OT billing officer: charge, linked cashier invoice and receipt.

Pre-op confirmations start unchecked and anesthesia starts pending. Editors load saved case evidence. Readiness/consent and actual anesthesia clearance precede surgery start; an operative note precedes completion. Completion changes the room to cleaning. The manager records inspection/change reasons before making it available again. A room with an active surgery cannot be released.

The theatre calendar uses the Dhaka date, including cases across UTC midnight. Local form times are sent with an explicit timezone. UI actions reflect role permissions and available workflow transitions; backend authorization remains authoritative.

Recorded OT charges are posted explicitly as real billing invoices. Repeated invoice posting for the same charge returns the existing invoice. Money is collected against that invoice; entering a charge cannot claim it was paid. Consumable/equipment usage records are not a new physical inventory-issue integration, and recorded usage charges are not automatically a complete consolidated theatre bill. Review the case's charge/inventory reconciliation separately.

## Reproducing local browser acceptance

Start the migrated local backend and frontend, then run:

```sh
npm run test:erp:api
npm run test:specialists:browser
```

The browser command creates dedicated synthetic users and a patient in local `hms_dev`/`hms_erp_test`, signs in with normal passwords, and performs operational writes using visible controls. It also makes read-only persistence assertions and separate negative authorization probes. There is no superadmin fallback. Ten accounts cover lab, radiology, blood bank, OT manager, surgeon, anesthetist, OT nurse, OT billing, cashier and patient.

Artifacts: `/tmp/hms-specialist-browser` and `/tmp/hms-specialist-browser-final.log`. Credentials live only in mode-0600 `/tmp/hms-specialist-fixtures.json`; never include that file in a commit or handoff. Fresh fixtures are the default. `HMS_E2E_RESUME=1` supports debugging an existing run and must be labeled as resumed evidence.

Synthetic screens and records are not clinical validation, actual surgery/transfusion/destruction, printer calibration, DICOM/PACS acceptance or a production deployment. Preserve test financial and clinical audit history; do not delete it to clean up the development database.
