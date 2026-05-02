export interface MenuItem {
  label: string;
  icon: string;
  permissions: string[];
  route?: string;
  children?: MenuItem[];
}

export const menuConfig: MenuItem[] = [
  { label: 'My Portal', icon: 'doctor', route: '/portal', permissions: ['patient.portal.view'] },
  { label: 'Dashboard', icon: 'dashboard', route: '/dashboard', permissions: ['dashboard.view'] },
  { label: 'Appointments', icon: 'list', route: '/appointments', permissions: ['appointment.manage'] },
  {
    label: 'Patients',
    icon: 'patients',
    permissions: ['patient.view'],
    children: [
      { label: 'All Patients', icon: 'list', route: '/patients', permissions: ['patient.view'] },
      { label: 'New Patient', icon: 'plus-user', route: '/patients/new', permissions: ['patient.create'] },
    ],
  },
  {
    label: 'Billing',
    icon: 'billing',
    permissions: ['billing.view'],
    children: [
      { label: 'Invoices', icon: 'receipt', route: '/billing', permissions: ['billing.invoice.create'] },
      { label: 'New Bill', icon: 'plus-user', route: '/billing/create', permissions: ['billing.invoice.create'] },
      { label: 'Due Payments', icon: 'list', route: '/billing/due-payments', permissions: ['billing.invoice.create'] },
      { label: 'Services', icon: 'service', route: '/billing/services', permissions: ['billing.service.manage'] },
      { label: 'Settings', icon: 'settings', route: '/billing/settings', permissions: ['billing.service.manage'] },
    ],
  },
  {
    label: 'OPD',
    icon: 'opd',
    permissions: ['opd.view'],
    children: [
      { label: 'Visits', icon: 'list', route: '/opd', permissions: ['opd.view'] },
      { label: 'New Visit', icon: 'plus-user', route: '/opd/register', permissions: ['opd.view'] },
      { label: 'Settings', icon: 'settings', route: '/opd/settings', permissions: ['settings.user.manage'] },
    ],
  },
  { label: 'IPD', icon: 'ipd', route: '/ipd', permissions: ['ipd.view'] },
  {
    label: 'ER',
    icon: 'service',
    permissions: ['er.view'],
    children: [
      { label: 'Overview', icon: 'dashboard', route: '/er', permissions: ['er.view'] },
      { label: 'Arrival', icon: 'plus-user', route: '/er/register', permissions: ['er.visit.manage'] },
    ],
  },
  {
    label: 'OT',
    icon: 'calendar',
    permissions: ['ot.view'],
    children: [
      { label: 'Dashboard', icon: 'dashboard', route: '/ot', permissions: ['ot.view'] },
      { label: 'Bookings', icon: 'plus-user', route: '/ot/bookings', permissions: ['ot.view'] },
      { label: 'Calendar', icon: 'calendar', route: '/ot/calendar', permissions: ['ot.view'] },
      { label: 'Rooms', icon: 'ipd', route: '/ot/rooms', permissions: ['ot.room.manage'] },
      { label: 'Pre-Op', icon: 'list', route: '/ot/checklist', permissions: ['ot.preop.manage'] },
      { label: 'Anesthesia', icon: 'service', route: '/ot/anesthesia', permissions: ['ot.anesthesia.manage'] },
      { label: 'Case Sheet', icon: 'receipt', route: '/ot/case-sheet', permissions: ['ot.view'] },
      { label: 'Recovery', icon: 'patients', route: '/ot/recovery', permissions: ['ot.recovery.manage'] },
      { label: 'Consumables', icon: 'service', route: '/ot/consumables', permissions: ['ot.inventory.manage'] },
      { label: 'Billing', icon: 'billing', route: '/ot/billing', permissions: ['ot.billing.manage'] },
      { label: 'Documents', icon: 'receipt', route: '/ot/documents', permissions: ['ot.documents.manage'] },
      { label: 'Reports', icon: 'reporting', route: '/ot/reports', permissions: ['ot.reports.view'] },
    ],
  },
  {
    label: 'Inventory',
    icon: 'service',
    permissions: ['inventory.view'],
    children: [
      { label: 'Overview', icon: 'dashboard', route: '/inventory', permissions: ['inventory.view'] },
      { label: 'Items', icon: 'list', route: '/inventory/items', permissions: ['inventory.view'] },
      { label: 'Reagents', icon: 'lab', route: '/inventory/reagents', permissions: ['inventory.view'] },
      { label: 'Requests', icon: 'receipt', route: '/inventory/requests', permissions: ['inventory.view'] },
      { label: 'Reports', icon: 'reporting', route: '/inventory/reports', permissions: ['inventory.view'] },
    ],
  },
  {
    label: 'Diagnostics',
    icon: 'lab',
    permissions: ['laboratory.view'],
    children: [
      { label: 'Lab Worklist', icon: 'lab', route: '/laboratory', permissions: ['laboratory.view'] },
      { label: 'Radiology', icon: 'radiology', route: '/radiology', permissions: ['radiology.view'] },
      { label: 'Orders', icon: 'list', route: '/diagnostics/orders', permissions: ['laboratory.view'] },
      { label: 'Settings', icon: 'settings', route: '/diagnostics/settings', permissions: ['laboratory.view'] },
    ],
  },
  { label: 'Reporting', icon: 'reporting', route: '/reporting', permissions: ['reporting.view'] },
  {
    label: 'Pharmacy',
    icon: 'pharmacy',
    permissions: ['pharmacy.view'],
    children: [
      { label: 'Overview', icon: 'dashboard', route: '/pharmacy', permissions: ['pharmacy.view'] },
      { label: 'Sale', icon: 'billing', route: '/pharmacy/sales', permissions: ['pharmacy.view'] },
      { label: 'Sales List', icon: 'list', route: '/pharmacy/sales/list', permissions: ['pharmacy.view'] },
      { label: 'Medicines', icon: 'service', route: '/pharmacy/medicines', permissions: ['pharmacy.view'] },
      { label: 'Purchases', icon: 'receipt', route: '/pharmacy/purchases', permissions: ['pharmacy.view'] },
      { label: 'Returns', icon: 'list', route: '/pharmacy/returns', permissions: ['pharmacy.view'] },
      { label: 'Dispense', icon: 'pharmacy', route: '/pharmacy/dispense', permissions: ['pharmacy.dispense'] },
      { label: 'Settings', icon: 'settings', route: '/pharmacy/settings', permissions: ['pharmacy.view'] },
    ],
  },
  {
    label: 'HR & Payroll',
    icon: 'users',
    permissions: ['hr.view'],
    children: [
      { label: 'Dashboard', icon: 'dashboard', route: '/hr', permissions: ['hr.view'] },
      { label: 'Employees', icon: 'users', route: '/hr/employees', permissions: ['hr.view'] },
      { label: 'Attendance', icon: 'list', route: '/hr/attendance', permissions: ['hr.attendance.manage'] },
      { label: 'Duty Roster', icon: 'calendar', route: '/hr/roster', permissions: ['hr.shift.manage'] },
      { label: 'Leave', icon: 'list', route: '/hr/leave', permissions: ['hr.leave.manage'] },
      { label: 'Payroll', icon: 'billing', route: '/hr/payroll', permissions: ['hr.payroll.manage'] },
      { label: 'Recruitment', icon: 'plus-user', route: '/hr/recruitment', permissions: ['hr.recruitment.manage'] },
      { label: 'Performance', icon: 'reporting', route: '/hr/performance', permissions: ['hr.performance.manage'] },
      { label: 'Reports', icon: 'reporting', route: '/hr/reports', permissions: ['hr.reports.view'] },
      { label: 'Settings', icon: 'settings', route: '/hr/settings', permissions: ['hr.settings.manage'] },
    ],
  },
  {
    label: 'Accounting',
    icon: 'accounting',
    permissions: ['accounting.view'],
    children: [
      { label: 'Dashboard', icon: 'dashboard', route: '/accounting', permissions: ['accounting.view'] },
      { label: 'Accounts', icon: 'list', route: '/accounting/accounts', permissions: ['accounting.view'] },
      { label: 'Collection', icon: 'billing', route: '/accounting/collections', permissions: ['accounting.view'] },
      { label: 'Receivables', icon: 'receipt', route: '/accounting/receivables', permissions: ['accounting.view'] },
      { label: 'Payables', icon: 'receipt', route: '/accounting/payables', permissions: ['accounting.view'] },
      { label: 'Expenses', icon: 'service', route: '/accounting/expenses', permissions: ['accounting.view'] },
      { label: 'Payroll', icon: 'users', route: '/accounting/payroll', permissions: ['accounting.view'] },
      { label: 'Cash/Bank', icon: 'accounting', route: '/accounting/cash-closing', permissions: ['accounting.view'] },
      { label: 'Journals', icon: 'list', route: '/accounting/journals', permissions: ['accounting.journal.post'] },
      { label: 'Reports', icon: 'reporting', route: '/accounting/reports', permissions: ['accounting.reports.view'] },
    ],
  },
  {
    label: 'Administration',
    icon: 'admin',
    permissions: ['settings.user.manage'],
    children: [
      { label: 'Configuration', icon: 'settings', route: '/configuration', permissions: ['settings.configuration.manage'] },
      { label: 'Users', icon: 'users', route: '/admin/users', permissions: ['settings.user.manage'] },
      { label: 'Roles', icon: 'shield', route: '/admin/roles', permissions: ['settings.role.manage'] },
    ],
  },
];
