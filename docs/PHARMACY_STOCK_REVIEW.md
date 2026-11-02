# Physical returns, stock review and disposal

Open **Pharmacy → Stock Review** (`/pharmacy/stock-review`). The four sections keep daily entry separate from supervisor decisions.

## Physical return

In Dispense, open the issued record, select its original issue/batch, enter quantity and reason and attest physical receipt/inspection. Leave saleable stock unchecked for damaged or unfit goods. Only suitable, unexpired goods may restore the original batch/store. Receipt retries do not add stock twice. Cashiers subsequently post a linked invoice credit; the receipt itself does not pay cash or authorize a replacement prescription.

## Stock count

A user with `pharmacy.stock.adjust` selects the original inventory batch/store, enters the measured physical count, count-sheet reference and reason. This captures the batch/store/item quantities, reservations and cost at submission. No stock changes until a different user with `pharmacy.stock.approve` approves it.

Approval posts a ledger difference and updates batch quantity/cost, store balance and item quantity/value in one transaction. If those quantities, reservations or cost changed since submission, reject the stale review and count again. Reserved quantities cannot be silently consumed. Repeated approval cannot post the correction twice. This workflow targets unified inventory batches; direct legacy pharmacy catalog adjustments retain their existing controls.

## Historical return allocations

Select a historical dispense whose returned quantity lacks original-source history. Allocate an evidenced quantity to an actual original issue, provide the historical document reference and record whether it was previously restocked, previously disposed, or remains held for disposal. A different supervisor reviews the evidence.

Approval records provenance only: it never restores historical stock a second time and never changes the recorded returned total. Original issue and unallocated return limits are checked again during approval. If evidence cannot establish provenance, leave the case unresolved; count stock separately rather than inventing a batch history.

## Disposal record and sign-off

Non-saleable return receipts appear in Disposal. After the disposal event, enter its actual method, time, witness reference, manifest/evidence reference and observations. This is an accountable record of the event, not an instruction to perform a disposal method. Whole receipt quantities are submitted together.

A different authorized supervisor approves or rejects the record in Reviews. Rejected submissions can be corrected and resubmitted; earlier records remain in audit history. Approved or already submitted receipts cannot receive duplicate disposal records. Stock and invoice balances are unchanged by sign-off. The UI and API do not verify external manifests or a witness's physical presence; the reviewer must inspect the actual evidence.

## Permissions and deployment

Apply migration `20261101_0068`. It creates durable stock reviews and the separate `pharmacy.stock.approve` permission, assigns that permission to existing Admin/Super Admin roles, and repairs the standard Receptionist role's branch-scoped doctor-wise OPD read access. Assign stock-approval permission to the hospital's designated reviewers through administration; it is deliberately not granted to every dispensing user.

Branch checks apply to source records and reviews. A submitter cannot approve or reject their own record even if they also have approval permission. Count evidence and disposal receipt evidence are retained with submitter, reviewer, decision note and timestamps.

## Local acceptance

`npm run test:roles:workflow:browser` creates dedicated synthetic accounts, stock and a bed in a local development/test database and then uses real password logins and visible browser controls. It covers reception, doctor, cashier, supervisor, patient, pharmacist and nurse. All workflow writes use UI controls; fixture setup and read-only persistence assertions use the database. No superadmin fallback exists in this browser journey. It does not destroy real goods or use real patients.

Private credentials live only in `/tmp/hms-browser-role-fixtures.json` with mode 0600. Browser screenshots/report are in `/tmp/hms-role-write-browser`. A fresh run is the default; `HMS_E2E_RESUME=1` is an explicit debugging option and must not be represented as an uninterrupted fresh run.
