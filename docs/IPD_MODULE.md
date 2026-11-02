# IPD operations and verification

## Patient flow

1. Open `/ipd/admit` for a direct admission, or convert a completed OPD consultation. Select the patient, registered available bed and treating doctor. Admission times are entered locally and submitted with a timezone.
2. Open `/ipd/admissions/{id}`. Clinical Work contains doctor notes, nursing rounds/vitals, treatment orders, medication administration and shift handovers. Saved notes and readings remain viewable after discharge.
3. Select a scheduled medication with **Record** to preserve its order, medicine, dose, route and due time. Administration completes its corresponding nursing task. Held/refused/skipped/delayed doses require a reason. Duplicate entries require explicit clinical approval permission and a reason.
4. Stop treatment with **Discontinue** and enter the reason. This cancels pending doses and tasks, preserves completed care, and prevents further administration against that order. A medicine already administered remains subject to billing; stopping future doses does not erase its charge. Review actual pharmacy quantities before posting charges; administration is not a pharmacy stock-return transaction.
5. Laboratory/radiology verification completes the linked IPD order. An IPD status update cannot bypass department verification. IPD-only investigations retain the admission reference without requiring an OPD visit.
6. Transfer the patient using **Transfer**. The old bed becomes cleaning; the new bed becomes occupied; the rate history retains both stays. Transfer dates cannot precede the admission or last bed assignment.
7. In `/ipd/settings`, expand **Cleaning and availability** on an unoccupied bed. Record cleaning/inspection or maintenance notes and mark it available, cleaning, maintenance or blocked. This requires `ipd.bed.manage`. An occupied bed cannot be manually released.
8. Billing shows bed/rate history, original bills, pending charges and clearance. Collect payments through Billing. The intake **Expected Advance** field is planning information; entering it does not collect cash or issue a receipt.
9. Request discharge, obtain doctor approval, enter the discharge condition/diagnosis/summary and complete department/billing clearances. Finalize discharge. Closed admissions retain notes, orders, medication history, movements and bills; new care writes are rejected.

## Bed charging policy

User-selected policy: **one daily charge at the highest bed rate used that day**, using `Asia/Dhaka` calendar dates.

- `ipd_bed_stays` records bed, ward, start/end times and the rate when occupied.
- Bed changes and later catalog changes do not reprice earlier recorded stays.
- A stay ending exactly at midnight does not charge an extra day for the vacated bed.
- Each new bed charge retains `bed_charge_date` on its invoice line.
- If a day was already billed and the patient upgrades later that day, the next draft bills only the unbilled difference. Final reconciliation carries the original interim line and the difference; it does not charge two full bed days.
- Billing readiness and the patient billing summary use the same outstanding-charge calculation.
- Zero-rate stays without other charges do not require fabricated paid invoices.
- If additional treatment/bed charges arise after a final invoice, use **Bill additional charges** and settle the additional bill before discharge. **Open final invoice** opens the posted document rather than creating a duplicate.

Migration `20261031_0065` creates the stay ledger and invoice charge date. Existing admissions are backfilled with their last recorded admission rate, explicitly marked **estimated**. Earlier bed-rate changes were never stored and cannot be reconstructed reliably. The UI and billing draft show this limitation; review legacy rates before posting historical charges.

## Data integrity and screen behavior

- Admissions and bed changes lock the patient/bed/admission rows. Registered bed labels resolve to the same bed even if the client omits the UUID; labels cannot bypass occupancy. Bed lookup is case-insensitive.
- Treatment orders cannot be silently reopened after completion/cancellation/discontinuation. New department orders revoke previous clearance.
- Nursing task/order changes are rejected on closed admissions. Handovers can be acknowledged once by the designated receiver; open handovers may be claimed by authorized ward staff. Receivers must be active and branch-compatible.
- The patient workspace avoids loading global dashboard analytics. Loading/retry feedback, preserved forms on errors, pending-action guards and closed-record states are explicit.
- Popups use responsive fields, accessible close buttons, focus return, keyboard focus containment and Escape handling. Notes, nursing readings and rate history have readable disclosures. Dashboard billing counts no longer treat every active admission as an unpaid bill.

## Verification

Run against local development services only:

```sh
npm run test:erp:api
CI=true npm --prefix frontend run build
CI=true CHROME_BIN='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' npm --prefix frontend test -- --watch=false --browsers=ChromeHeadless
npm run test:ipd:browser
npm run test:erp:ui
```

The API suite includes `backend/tests/test_ipd_lifecycle.py`: bed turnover and occupancy bypass, stopped doses/tasks, clearance invalidation, unique investigations, receiver acknowledgment, closed-record writes, Dhaka midnight/highest-rate accounting, interim-to-final rate adjustments, free beds, department verification, and delivered medication billing.

The expanded IPD browser journey runs registration/OPD first, then clicks doctor/nursing notes, orders, medication recording, discontinuation, transfer, bed cleaning completion, final payment, discharge approval/finalization, and closed-record viewing. It asserts a 300 → 500 same-day transfer charges 500 for the bed, plus 20 for the administered test medication. Synthetic bed provisioning still uses the API. It also captures a 390px clinical popup.

Artifacts: `/tmp/hms-ipd-browser/` and `/tmp/hms-ipd-audit/`. The route audit covers 11 routes at 1440px and 390px, including IPD overview and settings. Generated synthetic patients/beds remain in the local development database. Reruns may cancel abandoned active queue tokens whose labels contain this runner's `ERPBrowser Synthetic` prefix; ordinary patients are not touched.

Latest verified run: backend 62 passed and one existing expected failure for unpaid invoice returns; frontend 28 passed; production build passed; browser journey 16 stages passed; route audit 22 checks without captured API/JavaScript errors. This is targeted local coverage, not certification of every staff role, insurance/deposit/accounting scenario or physical device. See `CLAUDE_HANDOFF.md` and `INDEPENDENT_REVIEW.md` for the broader ERP review.

Clinical popups now keep save errors inline, trap keyboard focus, return focus to the trigger on close, and hide the floating assistant while open. The clinical note history shows full saved notes and nursing vital readings, including after discharge.
