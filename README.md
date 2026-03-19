# Hospital + Diagnostic Center Management System

Production-grade starter for a module-based Hospital and Diagnostic Center Management System with FastAPI, PostgreSQL, SQLAlchemy 2.0, Alembic, JWT auth, RBAC, audit logging, and an Angular enterprise frontend.

## High-Level Architecture

### Backend

- FastAPI application with `/api/v1` versioned router composition
- SQLAlchemy 2.0 entities with repository and service layers per module
- JWT short-lived access token plus DB-persisted refresh token rotation
- RBAC plus direct user permission overrides
- Protected endpoints through reusable permission dependencies
- Structured request logging, centralized exception handling, CORS, and health endpoints
- Audit logging for login, logout, user creation, role-permission updates, patient create, dispense, and accounting post

### Frontend

- Angular standalone application with feature-folder organization
- Centralized auth/session services using RxJS `BehaviorSubject`
- Functional interceptors for bearer token injection, refresh-on-401, and error normalization
- Route guards and structural directive for permission-aware rendering
- Centralized feature services for patients, pharmacy, accounting, and admin
- Permission-filtered sidebar menu and protected route metadata

## Backend Tree

```text
backend/
  app/
    api/v1/router.py
    core/
      config.py
      database.py
      exceptions.py
      logging.py
      security.py
    dependencies/
      auth.py
      permissions.py
    middleware/request_logging.py
    models/
      accounting.py
      audit_log.py
      base.py
      branch.py
      department.py
      patient.py
      permission.py
      pharmacy.py
      refresh_token.py
      role.py
      user.py
    modules/
      accounting/
      admin/
      audit/
      auth/
      branches/
      departments/
      patients/
      permissions/
      pharmacy/
      roles/
      users/
    schemas/
      accounting.py
      audit.py
      auth.py
      branch.py
      common.py
      department.py
      patient.py
      permission.py
      pharmacy.py
      role.py
      user.py
    scripts/seed.py
    utils/
      enums.py
      responses.py
      seed_data.py
    main.py
  alembic/
    env.py
    versions/20260319_0001_initial.py
  .env.example
  alembic.ini
  requirements.txt
```

## Frontend Tree

```text
frontend/
  angular.json
  package.json
  tsconfig.json
  tsconfig.app.json
  src/
    index.html
    main.ts
    styles.scss
    environments/environment.ts
    app/
      app.component.ts
      app.component.html
      app.config.ts
      app.routes.ts
      core/
        constants/permissions.ts
        guards/
        interceptors/
        models/auth.models.ts
        services/
      features/
        accounting/
        admin/
        auth/
        dashboard/
        patients/
        pharmacy/
      layouts/
        app-layout/
        auth-layout/
      navigation/
        menu.config.ts
        sidebar/
      shared/
        directives/has-permission.directive.ts
```

## Implemented Modules

- Authentication
- Users
- Roles
- Permissions
- Branches
- Departments
- Audit
- Patients
- Pharmacy
- Accounting
- Admin settings endpoints

## Core API Endpoints

### Authentication

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`

### Protected examples

- `GET /api/v1/patients/{id}` requires `patient.view`
- `POST /api/v1/patients` requires `patient.create`
- `POST /api/v1/pharmacy/dispense` requires `pharmacy.dispense`
- `POST /api/v1/accounting/journal/post` requires `accounting.journal.post`
- `GET /api/v1/admin/users` requires `settings.user.manage`

## Permission Framework

Naming follows:

- `module.action`
- `module.submodule.action`

Examples in the seeded catalog:

- `dashboard.view`
- `patient.view`
- `patient.create`
- `pharmacy.dispense`
- `accounting.journal.post`
- `settings.user.manage`
- `settings.role.manage`
- `settings.permission.manage`
- `audit.view`

Backend enforcement is done in [`backend/app/dependencies/permissions.py`](/Users/sahidulislam/ATM/HMS/backend/app/dependencies/permissions.py).

Frontend route protection is defined in [`frontend/src/app/app.routes.ts`](/Users/sahidulislam/ATM/HMS/frontend/src/app/app.routes.ts), [`frontend/src/app/core/guards/auth.guard.ts`](/Users/sahidulislam/ATM/HMS/frontend/src/app/core/guards/auth.guard.ts), [`frontend/src/app/core/guards/permission.guard.ts`](/Users/sahidulislam/ATM/HMS/frontend/src/app/core/guards/permission.guard.ts), and [`frontend/src/app/shared/directives/has-permission.directive.ts`](/Users/sahidulislam/ATM/HMS/frontend/src/app/shared/directives/has-permission.directive.ts).

## Authentication Flow

1. User posts credentials to `/api/v1/auth/login`.
2. Backend validates the user, resolves effective permissions, issues access and refresh tokens, persists the refresh token, and writes an audit entry.
3. Angular `AuthService` stores tokens, pushes the current user into `SessionService`, and routes into the protected shell.
4. Interceptors attach the access token on each request.
5. On `401`, the auth interceptor refreshes once using the persisted refresh token and retries the original request.
6. Logout invalidates the refresh-token session and clears client session state.

## Example Business Flows

### View patient

- Frontend route requires `patient.view`
- Backend endpoint `/api/v1/patients` validates `patient.view`
- Patient list is scoped by branch where relevant

### Create patient

- Angular create page posts through `PatientService`
- Backend validates payload, assigns patient number, persists record
- Audit log entry is written with action `patient.create`

### Pharmacy dispense

- Angular dispense page posts through `PharmacyService`
- Backend requires `pharmacy.dispense`
- Dispense record is created and audit logged

### Accounting journal post

- Angular journal page posts through `AccountingService`
- Backend validates balanced debit/credit and requires `accounting.journal.post`
- Journal is posted and audit logged

### Role management

- Admin role page loads roles and permission catalog
- Backend update endpoint replaces role-permission mappings
- Permission changes are applied on next `/auth/me` fetch or token refresh/login

## Setup Instructions

### Backend

1. Create and activate a Python virtual environment.
2. Install packages:

```bash
cd backend
pip install -r requirements.txt
```

3. Create environment file:

```bash
cp .env.example .env
```

4. Update `DATABASE_URL` and `SECRET_KEY` in `.env`.
5. Run migrations:

```bash
alembic upgrade head
```

6. Seed starter data:

```bash
PYTHONPATH=. python -m app.scripts.seed
```

7. Start the API:

```bash
PYTHONPATH=. uvicorn app.main:app --reload
```

### Frontend

1. Install dependencies:

```bash
cd frontend
npm install
```

2. Start Angular:

```bash
npm start
```

3. Open `http://localhost:4200`.

### Default Seed Login

- Username: `superadmin`
- Password: `Admin123!`

Change this immediately outside local development.

## Production Hardening Notes

- Move refresh tokens to secure `HttpOnly` cookies for production browser deployments
- Add rate limiting at login, refresh, and other sensitive endpoints
- Add field-level encryption where required by compliance policy
- Expand branch/department/own-record scope enforcement beyond the starter branch checks
- Add CSRF mitigation if cookie-based auth is adopted
- Add background jobs, async events, and outbox pattern for downstream integrations
- Add full test coverage and CI gates before release

## Roadmap

### Phase 1

- Stabilize auth, RBAC, admin settings, patients, pharmacy, accounting
- Add automated tests for auth flows and permission dependencies

### Phase 2

- Add appointments, admission/bed management, EMR, lab, radiology, billing, inventory
- Add reporting and audit search filters

### Phase 3

- Multi-branch operational policies, branch switching, tenant-aware reporting
- Workflow orchestration, notifications, and integration adapters

## Additional Documentation

- [`docs/architecture.md`](/Users/sahidulislam/ATM/HMS/docs/architecture.md)
