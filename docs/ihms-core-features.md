# IHMS Core Features, Gaps, And Delivery Plan

This file is the working source of truth for the Integrated Hospital Management System scope.

It combines:

- Requirements recoverable from `BrochureHospital.pdf`
- Requirements recoverable from `CPH_IHMS_Work_Order_21.pdf`
- Logical features that a production-ready hospital system should include even where the documents were vague
- Gap analysis against the current repo, where several modules exist but are still shallow or not fully integrated

This file should be used as the implementation backlog. We will build these features one integrated slice at a time.

## Current Repo Reality

Modules already present in the repo:

- Authentication
- Users
- Roles
- Permissions
- Branches
- Departments
- Audit
- Patients
- Appointments
- OPD
- IPD
- Laboratory
- Radiology
- Pharmacy
- Billing
- Accounting
- Reporting
- Patient portal
- Admin settings

Important clarification:

- Presence of a module does not mean feature completeness.
- Several modules exist as starters, but they still need proper workflow depth, automation, cross-module integration, and UI polish.

## High-Priority Maturity Gaps In Existing Modules

These are the areas that already exist but need major feature depth.

### OPD Maturity Gaps

- Existing patient auto-fill by health card / QR / barcode / phone / patient ID
- New vs existing patient flow split at registration/consultation
- Visit reuse and follow-up visit creation
- Doctor-wise consultation queue
- E-prescription generation
- QR/barcode-enabled prescription
- Prescription print / download
- Medication, investigation, and procedure ordering from the same consultation
- Consultation fee and service billing integration
- Visit status lifecycle
  - waiting
  - in consultation
  - prescribed
  - billed
  - completed
- Consultation notes and diagnosis history
- Follow-up advice and revisit scheduling
- Cross-referral and second opinion flow
- OPD payment collection, due tracking, and refund support

### IPD Maturity Gaps

- Existing patient auto-fill at admission
- Bed/ward/cabin selection with live occupancy
- Admission source tracking
- transfer workflow
- patient movement timeline
- doctor visit entry
- nurse station tasking
- requisition workflow
- inpatient medicine issue tracking
- service consumption tracking
- doctor visit billing
- nursing notes
- vitals charting
- progress notes
- OT booking integration
- discharge workflow with summary, certificate, and final billing
- deposit, advance, due, and refund support

### Billing Maturity Gaps

- Unified billing across OPD/IPD/lab/radiology/pharmacy/services
- Patient wallet/advance ledger
- Existing invoice lookup by patient
- Partial payment
- due settlement
- discount and package application
- refund approval workflow
- doctor share / hospital share distribution
- audit-safe bill cancellation/voiding
- invoice print with QR/barcode

### Patient Record Maturity Gaps

- Longitudinal EMR timeline
- case record consolidation
- diagnosis history
- medication history
- investigation history
- radiology history
- billing history
- document uploads
- prescription archive

### Patient Portal Maturity Gaps

- Portal appointment booking and rescheduling
- Portal prescription and report download
- Portal payment visibility
- Portal communication inbox / notifications
- Portal profile and dependent management if needed

## Consolidated Core Feature Scope

Below is the full module-by-module scope. This includes document-backed features plus logical features required for a coherent system.

## 1. Platform, Identity, and Access Control

- Login
- Refresh token session
- Logout
- Role-based access control
- Direct permission override
- Branch-scoped access
- Department-scoped access
- Own-record access where needed
- Audit trail for sensitive actions
- Session/device visibility
- Password reset/change
- Staff account lock/unlock
- Patient account registration and self-service access

## 2. Master Data and Setup

- Company information
- Branch information
- Department information
- Doctor information
- Employee information
- Service catalog
- Test catalog
- Investigation profile/package
- Item / charge heads
- OT master data
- Bed / ward / cabin master data
- Anesthesia type setup
- Operation name setup
- Electronic signature setup
- Notification templates
- Form / print / prescription template setup

## 3. Information Desk and Enquiry Desk

- Patient enquiry
- Appointment enquiry
- Investigation enquiry
- In-patient enquiry
- Cabin / bed enquiry
- Admit patient lookup
- Doctor schedule enquiry
- Package and service enquiry
- Bill status enquiry
- Report status enquiry
- Counter-wise desk interface
- Quick patient search by:
  - patient ID
  - phone
  - health card
  - QR / barcode
  - name

## 4. Queue Management

- Registration queue
- Doctor consultation queue
- Sample collection queue
- Report delivery queue
- Pharmacy queue
- Multi-counter queue support
- Bengali and English token display
- LED/LCD waiting display support
- Call / recall / skip / hold token
- Doctor room-wise queue
- Counter-wise queue analytics

## 5. Patient Registration and Identity

- New patient registration
- Existing patient search and auto-fill
- Patient registration number
- Health card generation
- QR / barcode patient card
- Duplicate patient detection
- Sponsor / company / corporate patient mapping
- Demographic details
- emergency contact
- address
- blood group
- identity fields if needed
- merge duplicate patient records with audit

## 6. Appointment and Scheduling

- Doctor schedule and room setup
- Appointment booking from:
  - front desk
  - phone
  - website
  - mobile app
- Search by department
- Search by doctor
- Slot-wise booking
- token / serial generation
- SMS / notification on booking
- Reschedule
- cancellation
- no-show marking
- appointment list and status report
- doctor-wise booking board
- appointment-to-OPD conversion

## 7. OPD Module

- Existing patient auto-fill on arrival
- Walk-in registration
- Appointment check-in
- Token generation and waiting flow
- Visit creation
- Consultation screen
- Chief complaint
- history of present illness
- past history
- vitals
- examination
- provisional / final diagnosis
- doctor notes
- follow-up advice
- consultation attachments
- medication order entry
- investigation order entry
- procedure order entry
- referral entry
- E-prescription generation
- QR / barcode enabled prescription
- prescription print and archive
- previous visit and prescription history
- consultation billing integration
- payment collection / due / refund
- visit closure and reporting

## 8. EMR / Longitudinal Patient Record

- Single patient timeline
- Visit timeline across OPD and IPD
- prescription history
- diagnosis history
- medication history
- investigation history
- radiology history
- procedure history
- allergy list
- chronic disease list
- uploaded document / image archive
- doctor notes history
- billing and payment history

## 9. Doctor Portal

- Doctor dashboard
- Today’s appointment list
- Waiting patient queue
- In-consultation workflow
- E-prescription builder
- Favorite medication / investigation templates
- Previous prescription view
- prior diagnosis and case records
- patient investigation and radiology result review
- consultation analytics
- doctor signature integration

## 10. Billing and Financial Workflow

- OPD billing
- IPD billing
- Investigation billing
- Radiology billing
- Pharmacy billing
- service billing
- package billing
- Invoice with QR/barcode
- Advance/deposit collection
- partial payment
- due collection
- refund management
- discount approval
- corporate / sponsor billing
- doctor commission/distribution
- invoice cancellation / void with audit
- cash summary
- collection summary
- revenue summary

## 11. Sample Collection

- Billing-originated investigation request receipt
- Sample collection using QR / barcode
- Repeat sample collection
- recollection request
- sample type and container tracking
- phlebotomy / collection desk queue
- user-wise sample collection summary
- sample location/status tracking
- sample receive handoff to lab

## 12. Laboratory Information System (LIS)

- Test setup
- profile setup
- package setup
- analyzer mapping
- analyzer-wise reference mapping
- sample receive
- sample processing
- analyzer integration
- scheduled / rerun / repeat handling
- result entry
- result verification
- pathologist approval
- abnormal flag workflow
- critical value flagging
- barcode-based processing
- results publish to patient record and portal

## 13. Reagent and QC Management

- Analyzer-wise reagent lot entry
- reagent barcode mapping
- reagent in/out
- expiry alert
- stock alert
- QC lot mapping
- QC barcode generation
- QC result capture
- daily QC reporting
- analyzer lot traceability

## 14. Radiology Information System (RIS)

- Radiology order intake
- patient demographic sync
- modality worklist support
- RIS / MWL / PACS support
- radiology scheduling
- film/image archive
- template-based reporting
- technician workflow
- radiologist review and approval
- report publishing to patient record and portal

## 15. Pathology and Radiology Reporting

- Draft / check / approve flow
- report print
- patient report history
- report delivery queue
- result publication control
- revised report with audit

## 16. Pharmacy

- Prescription-linked dispensing
- prescription validation
- dispense partial / full
- patient medication history
- pharmacy queue
- pharmacy billing integration
- stock deduction
- substitution / unavailable item handling
- refill and repeat medication logic if needed

## 17. IPD / Indoor Management

- Admission
- existing patient auto-fill
- ward / cabin / bed assignment
- transfer
- transfer history
- occupancy management
- nurse station view
- daily progress charting
- service entry
- doctor visit entry
- nursing requisition
- medicine issue tracking
- diet / support services if needed
- discharge processing
- birth / death / discharge certificate generation
- deposit and final settlement
- doctor payment ledger
- indoor MIS

## 18. OT / Procedure / Surgery Management

- Anesthesia type setup
- operation name setup
- OT doctor schedule
- OT booking board
- OT reschedule
- OT patient preparation checklist
- OT team assignment
- anesthesia record
- operation notes
- OT charge entry
- doctor/guardian notification
- OT bill distribution

## 19. Bed, Ward, Cabin, ICU, CCU Management

- Bed map by floor/type
- occupancy tracking
- reserve/occupy/release bed
- transfer bed
- cleaning/maintenance hold
- cabin/ward-wise utilization

## 20. Patient Portal

- Patient profile
- appointment booking / reschedule / cancellation
- report history
- payment history
- e-prescription history
- package / offer visibility
- notifications
- downloadable invoice / receipt / report

## 21. Notifications and Communication

- SMS for appointment serial/token
- SMS for admission / transfer / OT / discharge
- SMS / email for report ready
- SMS / email for bill / payment acknowledgement
- doctor / guardian notifications
- notification log and retry status

## 22. Reporting, MIS, and Analytics

- Patient activity reports
- User activity reports
- Doctor activity reports
- OPD service and revenue reports
- IPD occupancy and revenue reports
- sample collection reports
- lab turnaround reports
- pharmacy revenue reports
- doctor payment ledger
- refund / due / collection analytics
- overall service rating
- department-wise rating
- executive dashboards

## 23. Accounting Integration

- Journal posting from billing events
- ledger mapping
- doctor payable mapping
- refund accounting
- revenue recognition hooks
- cash/bank summary

## 24. Logical Features To Add Even If Brochure Didn’t Explicitly Say So

These are necessary for a practical integrated system.

- Existing customer / existing patient auto-fill everywhere
  - registration
  - OPD
  - IPD
  - billing
  - sample collection
  - pharmacy
- Global patient search
- Reusable health card / QR scan entry across modules
- Cross-module event status
  - ordered
  - billed
  - collected
  - processed
  - verified
  - delivered
- Consistent audit for all critical business actions
- Role-based UI visibility per module action
- Printable artifacts
  - prescription
  - invoice
  - receipt
  - report
  - certificates
- Attachment support in clinical modules
- Activity timeline per patient
- Cancellation / void / refund controls with approval and audit
- Dashboard widgets per role
- Search, filters, and export in all operational lists

## Delivery Strategy

We will implement this as one integrated system, but in vertical slices that remain production-usable.

Each slice should include:

1. data model
2. migration
3. backend service and API
4. permission and audit integration
5. frontend list/detail/form flow
6. navigation and route protection
7. reporting hooks
8. polished UI states

## Recommended Delivery Order

### Phase 1: Identity, Front Office, and Existing Patient Reuse

1. Health card / QR / barcode patient identity workflow
2. Existing patient search and auto-fill service usable across OPD, IPD, billing, and sample collection
3. Information desk and enquiry desk
4. Queue management

### Phase 2: OPD As Full Revenue + Clinical Entry Flow

5. OPD consultation lifecycle hardening
6. E-prescription generation and prescription print/archive
7. OPD billing, payment, due, and refund integration
8. EMR visit history for OPD

### Phase 3: Investigation Pipeline

9. Investigation billing hardening
10. Sample collection workflow
11. LIS receive/process/verify/report workflow
12. Report delivery and patient portal result publishing

### Phase 4: IPD And OT

13. Bed / ward / cabin live operations
14. Admission / transfer / discharge lifecycle
15. Indoor billing and doctor visit workflow
16. OT booking and operation workflow

### Phase 5: Doctor, Patient, Pharmacy, And MIS

17. Doctor portal depth
18. Patient portal depth
19. Pharmacy integration hardening
20. Management dashboards and MIS reporting

### Phase 6: Advanced Diagnostic Integration

21. RIS / PACS / MWL depth
22. Reagent and QC management
23. Analyzer/device integrations

## Best First Implementation Step

If we want the most valuable next build immediately, start with:

- Existing patient search and auto-fill as a shared platform capability

Reason:

- It directly improves OPD, IPD, billing, lab, radiology, and pharmacy
- It is a prerequisite for a smooth hospital workflow
- It unlocks QR/health-card-driven navigation
- It reduces duplicate patient creation and makes the rest of the system feel integrated

If we want the next feature with the biggest visible business impact after that, do:

- OPD consultation + e-prescription + OPD payment integration
