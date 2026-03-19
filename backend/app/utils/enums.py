from enum import StrEnum


class AuditAction(StrEnum):
    LOGIN = "auth.login"
    LOGOUT = "auth.logout"
    USER_CREATE = "settings.user.create"
    ROLE_PERMISSION_UPDATE = "settings.role.permissions.update"
    PATIENT_CREATE = "patient.create"
    PHARMACY_DISPENSE = "pharmacy.dispense"
    ACCOUNTING_POST = "accounting.journal.post"

