PERMISSION_CATALOG = [
    ("dashboard.view", "dashboard", "view", "View dashboard"),
    ("patient.view", "patient", "view", "View patients"),
    ("patient.create", "patient", "create", "Create patients"),
    ("patient.edit", "patient", "edit", "Edit patients"),
    ("patient.delete", "patient", "delete", "Delete patients"),
    ("pharmacy.view", "pharmacy", "view", "View pharmacy module"),
    ("pharmacy.dispense", "pharmacy", "dispense", "Dispense medicine"),
    ("pharmacy.stock.adjust", "pharmacy", "stock.adjust", "Adjust pharmacy stock"),
    ("accounting.view", "accounting", "view", "View accounting"),
    ("accounting.journal.create", "accounting", "journal.create", "Create accounting journal"),
    ("accounting.journal.post", "accounting", "journal.post", "Post accounting journal"),
    ("settings.user.manage", "settings", "user.manage", "Manage users"),
    ("settings.role.manage", "settings", "role.manage", "Manage roles"),
    ("settings.permission.manage", "settings", "permission.manage", "Manage permission catalog"),
    ("settings.branch.manage", "settings", "branch.manage", "Manage branches"),
    ("settings.department.manage", "settings", "department.manage", "Manage departments"),
    ("audit.view", "audit", "view", "View audit logs"),
]

ROLE_CATALOG = {
    "SUPER_ADMIN": [code for code, *_ in PERMISSION_CATALOG],
    "ADMIN": [
        "dashboard.view",
        "patient.view",
        "patient.create",
        "pharmacy.view",
        "accounting.view",
        "settings.user.manage",
        "settings.role.manage",
        "settings.branch.manage",
        "settings.department.manage",
        "audit.view",
    ],
    "DOCTOR": ["dashboard.view", "patient.view", "patient.create"],
    "PHARMACIST": ["dashboard.view", "patient.view", "pharmacy.view", "pharmacy.dispense"],
    "ACCOUNTANT": ["dashboard.view", "accounting.view", "accounting.journal.create", "accounting.journal.post"],
}

