# SQLAlchemy Relationships Review

## Current Relationship Graph

### Access control

- `User.branch_id -> Branch.id`
- `User.department_id -> Department.id`
- `User <-> Role` via `user_roles`
- `Role <-> Permission` via `role_permissions`
- `User <-> Permission` via `user_permissions`
- `User -> RefreshToken` one-to-many
- `AuditLog.user_id -> User.id`

### Business entities

- `Patient.branch_id -> Branch.id`
- `PharmacyDispense.patient_id -> Patient.id`
- `PharmacyDispense.branch_id -> Branch.id`
- `PharmacyDispense.dispensed_by_user_id -> User.id`
- `AccountingJournal.branch_id -> Branch.id`
- `AccountingJournal.posted_by_user_id -> User.id`

## What Is Good

- Access control join tables are modeled cleanly and support both RBAC and direct permission overrides.
- `Branch` and `Department` already provide a reasonable base for branch-scoped access.
- `RefreshToken` is correctly modeled as persisted session state instead of stateless-only refresh handling.
- Business entities already include `created_by`, `updated_by`, `is_active`, and timestamps through mixins.

## Recommended Refinements

### 1. Add explicit reverse relationships where operational queries will need them

The current graph is valid, but these reverse collections will help for reporting and loader tuning:

- `User.audit_logs`
- `User.dispensed_records`
- `User.posted_journals`
- `Branch.dispenses`
- `Branch.accounting_journals`

These are not required for correctness, but they reduce ad hoc query shape later.

### 2. Add delete behavior intentionally

Current FKs rely on database defaults. For production systems, define the intended policy explicitly:

- Restrict deleting `Branch` if users, patients, dispenses, or journals exist
- Restrict deleting `Role` and `Permission` if assigned
- Restrict deleting `User` if referenced by audit or business records
- Consider soft-delete-only for master tables instead of physical delete

### 3. Add branch-scope indexes for common reads

Likely useful indexes:

- `patients(branch_id, created_at)`
- `pharmacy_dispenses(branch_id, created_at)`
- `accounting_journals(branch_id, created_at)`
- `audit_logs(user_id, created_at)`

### 4. Consider modeled scope rules later

If branch/department/own-record scope is central, add explicit policy columns or join tables instead of relying purely on application code:

- `roles.scope_type`
- `users.allowed_branch_id`
- `users.allowed_department_id`

### 5. Audit log should remain append-only

This table is correctly separate from `BaseModelMixin`. That is good. It should not support update/delete in normal application logic.

## Migration Draft Review

The initial migration is structurally aligned with the models and safe as a starter.

Recommended additions for the next revision:

- Add explicit indexes for high-volume operational filters
- Add check constraints where business invariants are known
  - `debit_amount >= 0`
  - `credit_amount >= 0`
  - `quantity > 0`
  - `unit_price >= 0`
- Add `server_default=sa.true()` or equivalent where desired for `is_active`
- Add `server_default=sa.text('now()')` to audit timestamps if logs may ever be inserted outside ORM code

## Neon Database Usage

Use the provided Neon PostgreSQL URL through `DATABASE_URL` at runtime.

Do not commit the credential into source files. Keep it in:

- local `.env`
- deployment secret manager
- CI/CD secret store

