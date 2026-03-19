from fastapi import APIRouter

from app.modules.accounting.router import router as accounting_router
from app.modules.admin.router import router as admin_router
from app.modules.audit.router import router as audit_router
from app.modules.auth.router import router as auth_router
from app.modules.branches.router import router as branches_router
from app.modules.billing.router import router as billing_router
from app.modules.departments.router import router as departments_router
from app.modules.patients.router import router as patients_router
from app.modules.permissions.router import router as permissions_router
from app.modules.pharmacy.router import router as pharmacy_router
from app.modules.roles.router import router as roles_router
from app.modules.users.router import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(roles_router)
api_router.include_router(permissions_router)
api_router.include_router(branches_router)
api_router.include_router(departments_router)
api_router.include_router(audit_router)
api_router.include_router(billing_router)
api_router.include_router(patients_router)
api_router.include_router(pharmacy_router)
api_router.include_router(accounting_router)
api_router.include_router(admin_router)
