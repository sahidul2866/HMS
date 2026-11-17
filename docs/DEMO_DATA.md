# Database and demo data

The local installation checked on 13 November 2026 uses **PostgreSQL 18.6**, database
`hms` on `localhost:5432`. The backend reads `DATABASE_URL` from `backend/.env`.

A GitHub push sends committed files, not PostgreSQL rows. `.env` and `.db_data/`
are ignored by Git. A separately hosted backend has its own database; it needs its
own migrations and demo seed run. These seed scripts are shareable source code.
The local database backup and patient records should remain outside Git.

## Demo login

| Account | Username | Password |
| --- | --- | --- |
| Patient with the complete preview records | `patient_demo` | `Patient123!` |
| Demo administrator | `admin_maya` | `Demo12345!` |
| Demo doctor | `dr_rahman` | `Demo12345!` |

Choose the Patient login for `patient_demo`. Its patient number is `PAT-DEMO-FULL`.
The bundled core seed also creates other demo staff and patient accounts.

## Run in Windows PowerShell

From `HMS/backend`, after configuring the local database and applying migrations:

```powershell
# First run in a fresh development database:
.venv\Scripts\python.exe -m app.scripts.seed_complete_demo --include-core

# Add only the complete preview dataset to an already seeded database:
.venv\Scripts\python.exe -m app.scripts.seed_complete_demo

# Optional per-table coverage report (the output folder must already exist):
.venv\Scripts\python.exe -m app.scripts.seed_complete_demo --report ../.db_data/demo-data-coverage.json
```

The complete-demo command accepts only `APP_ENV=development` and a localhost
database. It adds stable, named fixtures without overwriting existing records.
Re-running it preserves those fixtures and does not duplicate them. The optional
`--include-core` runs the repository's original demo scripts, which can refresh
bundled demo staff credentials and settings; use it for initial setup.

## What is included

The core datasets and complete preview cover patient care, OPD/IPD/ER, appointments,
lab/radiology, billing/accounting, pharmacy, inventory/reagents, HR/payroll, OT,
blood bank, catering, transport, telemedicine, queues, scanning and assistant logs.
By default, the complete preview's clinical records reference the synthetic Demo Preview
patient. Financial and clinical examples are synthetic UI fixtures, not evidence
that real payments or treatments occurred. Audit examples are marked `demo_seed`.
The Gemini example explicitly records that no external API call was made.

The four bundled demo doctors receive only missing weekly schedules. Existing
schedules are preserved. The appointment service currently interprets stored
schedule hours as UTC; the added 03:00–14:00 schedule corresponds to 09:00–20:00
Bangladesh time. The demo patient's appointment is created through the real booking
service, so it also reserves its slot.

The sample attachment is `frontend/src/assets/demo/sample-record.txt`. It is an
actual text file for checking downloads. PACS metadata is only a preview; no DICOM
images or video meetings are provisioned.

On the checked local installation, **210/210 tables contain rows**. This count
includes migration metadata, permissions and authentication tables, which are
populated by migrations, core setup and logins rather than fabricated credentials.
On a fresh database, sign in once with the demo staff and patient accounts to
exercise their session tables. The coverage report lists any still-empty tables.

The backup taken before adding demos is stored locally at
`.db_data/hms-before-demo-20261113-030133.dump`. It is a PostgreSQL custom-format
backup, not a file to commit or upload to GitHub.

## Show sample records in the patient account you are testing

The portal filters clinical history by the signed-in account's patient ID. Rows
belonging to `patient_demo` do not appear in another patient's portal. Table row
counts alone therefore do not verify what that patient can see.

For an explicitly selected patient in your local development database, run:

```powershell
.venv\Scripts\python.exe -m app.scripts.seed_patient_portal_demo --patient-number PAT-20261108153151-1571
```

This adds clearly labelled DEMO records to that patient: two visits and sample
prescriptions, verified lab and radiology reports, two invoices with payments,
pharmacy history, an active admission (only if none exists), a past admission with
a discharge document, and a completed appointment. It preserves existing records
and can be repeated without duplicates. The source patient for each clinical
record, its visit, and the report release status are linked so the portal can
actually display them. The same visible examples are included in the complete
seed for `patient_demo`.

Reload the portal or press **Refresh records**. Open Records → Documents to see
prescriptions, reports, invoices, receipts and a discharge summary. **Preview**
opens the selected record and **Download** saves its text summary. These examples
do not represent real treatment or real amounts payable.

## Pending billing queue examples

Run `python -m app.scripts.seed_pending_bills_demo` from `backend` with the
project virtual environment. This adds ten posted, unpaid invoices named
`DEMO-PENDING-01` through `DEMO-PENDING-10` for the synthetic Demo Preview patient.
Amounts range from BDT 100 to BDT 1,000, initially totaling BDT 5,500 due.
The overview previews six bills; **View all pending bills** opens the full list.
Search `DEMO-PENDING-` to isolate these examples. They also demonstrate referral
grouping under Dr. Rahman (eight invoices, BDT 3,600), Dr. Faria Islam (one,
BDT 1,000), and Dr. Arif Khan (one, BDT 900). Repeat runs preserve payments made during testing and
do not duplicate or reset invoices. These are synthetic local development charges.

## Patient booking behavior

Doctor **Profile** opens a dialog showing the stored qualifications, specialty,
chamber and fee. **Select for booking** fills the doctor in the booking form.
Choose a date, an available time and a reason, then use **Confirm Request**.
Missing data, loading failures and an already-booked slot are explained beside
the button; a pending request cannot be submitted twice.

Successful booking opens a visible confirmation with the reference, actual status,
doctor, Bangladesh appointment time, location and fee information. The checklist
explains bringing the patient ID/registered phone number, previous reports and
prescriptions, checking in at reception, and confirming fees at billing. Booking
does not collect payment. **Appointments → Details & next steps** reopens this
information after a refresh.
