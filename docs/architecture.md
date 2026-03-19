# HMS Architecture

## Backend

- FastAPI API with `/api/v1` versioned routers
- SQLAlchemy 2.0 models and repository/service layering
- JWT access token plus database-backed refresh token rotation
- RBAC and direct-permission override support
- Audit logging for authentication and sensitive domain writes
- Modular feature folders for auth, admin, patients, pharmacy, accounting, audit, and settings entities

## Frontend

- Angular standalone application with route-based feature folders
- `AuthService` and `SessionService` centralize session bootstrap, refresh, and logout
- Functional interceptors inject bearer tokens and retry once after refresh
- `authGuard`, `permissionGuard`, and `HasPermissionDirective` enforce UI access
- Shared menu configuration filters navigation by effective permissions

## Seeded Roles

- `SUPER_ADMIN`
- `ADMIN`
- `DOCTOR`
- `PHARMACIST`
- `ACCOUNTANT`

## Starter Business Flows

- Login and token refresh rotation
- Patient list and create
- Pharmacy dispense
- Accounting journal post
- User management and role permission updates
