from enum import StrEnum


class AuditAction(StrEnum):
    LOGIN = "auth.login"
    LOGOUT = "auth.logout"
    USER_CREATE = "settings.user.create"
    ROLE_PERMISSION_UPDATE = "settings.role.permissions.update"
    PATIENT_CREATE = "patient.create"
    BILLING_SERVICE_CREATE = "billing.service.create"
    BILLING_DOCTOR_CREATE = "billing.doctor.create"
    BILLING_INVOICE_CREATE = "billing.invoice.create"
    BILLING_INVOICE_VOID = "billing.invoice.void"
    PHARMACY_DISPENSE = "pharmacy.dispense"
    ACCOUNTING_POST = "accounting.journal.post"
