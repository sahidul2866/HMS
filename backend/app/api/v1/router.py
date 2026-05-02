from fastapi import APIRouter

from app.modules.accounting.router import router as accounting_router
from app.modules.appointments.router import router as appointments_router
from app.modules.admin.router import router as admin_router
from app.modules.audit.router import router as audit_router
from app.modules.auth.router import router as auth_router
from app.modules.branches.router import router as branches_router
from app.modules.billing.router import router as billing_router
from app.modules.configuration.router import router as configuration_router
from app.modules.departments.router import router as departments_router
from app.modules.diagnostics.router import router as diagnostics_router
from app.modules.hr.router import router as hr_router
from app.modules.ipd.router import router as ipd_router
from app.modules.laboratory.router import router as laboratory_router
from app.modules.opd.router import router as opd_router
from app.modules.ot.router import router as ot_router
from app.modules.er.router import router as er_router
from app.modules.patients.router import router as patients_router
from app.modules.permissions.router import router as permissions_router
from app.modules.patient_portal.router import router as patient_portal_router
from app.modules.patient_bot.router import router as patient_bot_router
from app.modules.staff_bot.router import router as staff_bot_router
from app.modules.patient_auth.router import router as patient_auth_router
from app.modules.pharmacy.router import router as pharmacy_router
from app.modules.inventory.router import router as inventory_router
from app.modules.radiology.router import router as radiology_router
from app.modules.reporting.router import router as reporting_router
from app.modules.roles.router import router as roles_router
from app.modules.users.router import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(appointments_router)
api_router.include_router(users_router)
api_router.include_router(roles_router)
api_router.include_router(permissions_router)
api_router.include_router(patient_portal_router)
api_router.include_router(patient_bot_router)
api_router.include_router(staff_bot_router)
api_router.include_router(patient_auth_router)
api_router.include_router(branches_router)
api_router.include_router(departments_router)
api_router.include_router(audit_router)
api_router.include_router(billing_router)
api_router.include_router(configuration_router)
api_router.include_router(opd_router)
api_router.include_router(ot_router)
api_router.include_router(er_router)
api_router.include_router(hr_router)
api_router.include_router(ipd_router)
api_router.include_router(diagnostics_router)
api_router.include_router(laboratory_router)
api_router.include_router(radiology_router)
api_router.include_router(reporting_router)
api_router.include_router(patients_router)
api_router.include_router(pharmacy_router)
api_router.include_router(inventory_router)
api_router.include_router(accounting_router)
api_router.include_router(admin_router)
