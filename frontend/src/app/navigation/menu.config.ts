export interface MenuItem {
  label: string;
  icon: string;
  permissions: string[];
  route?: string;
  children?: MenuItem[];
}

export interface MenuSection {
  label: string;
  items: MenuItem[];
}

export const menuSections: MenuSection[] = [
  {
    label: 'Workspace',
    items: [
      { label: 'My Portal', icon: 'doctor', route: '/portal', permissions: ['patient.portal.view'] },
      { label: 'Dashboard', icon: 'dashboard', route: '/dashboard', permissions: ['dashboard.view'] },
    ],
  },
  {
    label: 'Patient Flow',
    items: [
      {
        label: 'Patients',
        icon: 'patients',
        permissions: ['patient.view'],
        children: [
          { label: 'All Patients', icon: 'list', route: '/patients', permissions: ['patient.view'] },
          { label: 'New Patient', icon: 'plus-user', route: '/patients/new', permissions: ['patient.create'] },
          { label: 'ID Card Settings', icon: 'settings', route: '/patients/id-card-settings', permissions: ['patient.id_card.configure'] },
        ],
      },
      {
        label: 'OPD',
        icon: 'opd',
        permissions: ['opd.view'],
        children: [
          { label: 'Overview', icon: 'dashboard', route: '/opd', permissions: ['opd.view'] },
          { label: 'Visits', icon: 'list', route: '/opd/visits', permissions: ['opd.view'] },
          { label: 'OPD Queue', icon: 'list', route: '/opd/queue', permissions: ['opd.queue.view'] },
          { label: 'New Visit', icon: 'plus-user', route: '/opd/register', permissions: ['opd.visit.create'] },
          { label: 'Appointments', icon: 'calendar', route: '/appointments', permissions: ['appointment.view'] },
          { label: 'New Appointment', icon: 'plus-user', route: '/appointments/create', permissions: ['appointment.book'] },
          { label: 'Doctor Settings', icon: 'settings', route: '/opd/settings', permissions: ['opd.settings.manage'] },
          { label: 'Configuration', icon: 'settings', route: '/opd/configuration', permissions: ['opd.settings.manage'] },
        ],
      },
      {
        label: 'IPD',
        icon: 'ipd',
        permissions: ['ipd.view'],
        children: [
          { label: 'Overview', icon: 'dashboard', route: '/ipd', permissions: ['ipd.view'] },
          { label: 'Admissions', icon: 'list', route: '/ipd/admissions', permissions: ['ipd.view'] },
          { label: 'New Admission', icon: 'plus-user', route: '/ipd/admit', permissions: ['ipd.admit'] },
          { label: 'Settings', icon: 'settings', route: '/ipd/settings', permissions: ['ipd.settings.manage'] },
        ],
      },
      {
        label: 'ER',
        icon: 'service',
        permissions: ['er.view'],
        children: [
          { label: 'Overview', icon: 'dashboard', route: '/er', permissions: ['er.view'] },
          { label: 'New Arrival', icon: 'plus-user', route: '/er/register', permissions: ['er.visit.manage'] },
        ],
      },
    ],
  },
  {
    label: 'Revenue',
    items: [
      {
        label: 'Billing',
        icon: 'billing',
        permissions: ['billing.view'],
        children: [
          { label: 'Overview', icon: 'dashboard', route: '/billing', permissions: ['billing.view'] },
          { label: 'Invoices', icon: 'receipt', route: '/billing/list', permissions: ['billing.view'] },
          { label: 'New Bill', icon: 'plus-user', route: '/billing/create', permissions: ['billing.invoice.create'] },
          { label: 'Due Payments', icon: 'list', route: '/billing/due-payments', permissions: ['billing.view'] },
          { label: 'Services', icon: 'service', route: '/billing/services', permissions: ['billing.service.manage'] },
          { label: 'Settings', icon: 'settings', route: '/billing/settings', permissions: ['billing.service.manage'] },
        ],
      },
    ],
  },
  {
    label: 'Clinical Services',
    items: [
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
    label: 'Diagnostics',
    icon: 'lab',
    permissions: ['laboratory.view'],
    children: [
      { label: 'Lab Worklist', icon: 'lab', route: '/laboratory', permissions: ['laboratory.view'] },
      { label: 'LIS Simulator', icon: 'service', route: '/laboratory/lis-simulator', permissions: ['laboratory.view'] },
      { label: 'Radiology', icon: 'radiology', route: '/radiology', permissions: ['radiology.view'] },
      { label: 'Orders', icon: 'list', route: '/diagnostics/orders', permissions: ['diagnostics.order.manage'] },
      { label: 'Settings', icon: 'settings', route: '/diagnostics/settings', permissions: ['diagnostics.settings.manage'] },
    ],
  },
  {
    label: 'Blood Bank',
    icon: 'service',
    permissions: ['blood_bank.view'],
    children: [
      { label: 'Dashboard', icon: 'dashboard', route: '/blood-bank/dashboard', permissions: ['blood_bank.dashboard.view'] },
      { label: 'Queue', icon: 'list', route: '/blood-bank/queue', permissions: ['blood_bank.queue.manage'] },
      { label: 'Donors', icon: 'patients', route: '/blood-bank/donors', permissions: ['blood_bank.view'] },
      { label: 'Screening', icon: 'list', route: '/blood-bank/screening', permissions: ['blood_bank.donor.screen'] },
      { label: 'Collection', icon: 'plus-user', route: '/blood-bank/collection', permissions: ['blood_bank.collection.create'] },
      { label: 'Testing', icon: 'lab', route: '/blood-bank/testing', permissions: ['blood_bank.testing.update'] },
      { label: 'Components', icon: 'service', route: '/blood-bank/components', permissions: ['blood_bank.component.prepare'] },
      { label: 'Stock', icon: 'list', route: '/blood-bank/stock', permissions: ['blood_bank.stock.view'] },
      { label: 'Requests', icon: 'receipt', route: '/blood-bank/requests', permissions: ['blood_bank.view'] },
      { label: 'Crossmatch', icon: 'lab', route: '/blood-bank/crossmatch', permissions: ['blood_bank.crossmatch.perform'] },
      { label: 'Issue', icon: 'billing', route: '/blood-bank/issue', permissions: ['blood_bank.issue'] },
      { label: 'Transfusion', icon: 'service', route: '/blood-bank/transfusion', permissions: ['blood_bank.transfusion.update'] },
      { label: 'Return', icon: 'list', route: '/blood-bank/return', permissions: ['blood_bank.return'] },
      { label: 'Discard', icon: 'list', route: '/blood-bank/discard', permissions: ['blood_bank.discard'] },
      { label: 'Reports', icon: 'reporting', route: '/blood-bank/reports', permissions: ['blood_bank.report.view'] },
      { label: 'Settings', icon: 'settings', route: '/blood-bank/settings', permissions: ['blood_bank.component.prepare'] },
    ],
  },
  {
    label: 'Catering',
    icon: 'service',
    permissions: ['catering.view'],
    children: [
      { label: 'Dashboard', icon: 'dashboard', route: '/catering/dashboard', permissions: ['catering.dashboard.view'] },
      { label: 'Patient Diet Orders', icon: 'patients', route: '/catering/diet-orders', permissions: ['catering.view'] },
      { label: 'Kitchen Queue', icon: 'list', route: '/catering/kitchen', permissions: ['catering.kitchen_queue.view'] },
      { label: 'Meal Schedule', icon: 'calendar', route: '/catering/schedule', permissions: ['catering.settings.manage'] },
      { label: 'Delivery', icon: 'service', route: '/catering/delivery', permissions: ['catering.meal.deliver'] },
      { label: 'Staff Meals', icon: 'users', route: '/catering/staff-meals', permissions: ['catering.staff_meal.manage'] },
      { label: 'Inventory/Requisition', icon: 'receipt', route: '/catering/inventory', permissions: ['catering.kitchen_queue.view'] },
      { label: 'Reports', icon: 'reporting', route: '/catering/reports', permissions: ['catering.report.view'] },
      { label: 'Settings', icon: 'settings', route: '/catering/settings', permissions: ['catering.settings.manage'] },
    ],
  },
    ],
  },
  {
    label: 'Pharmacy & Stock',
    items: [
  {
    label: 'Pharmacy',
    icon: 'pharmacy',
    permissions: ['pharmacy.view'],
    children: [
      { label: 'Overview', icon: 'dashboard', route: '/pharmacy', permissions: ['pharmacy.view'] },
      { label: 'Sale', icon: 'billing', route: '/pharmacy/sales', permissions: ['pharmacy.sale.create'] },
      { label: 'Sales List', icon: 'list', route: '/pharmacy/sales/list', permissions: ['pharmacy.view'] },
      { label: 'Medicines', icon: 'service', route: '/pharmacy/medicines', permissions: ['pharmacy.view'] },
      { label: 'Purchases', icon: 'receipt', route: '/pharmacy/purchases', permissions: ['pharmacy.purchase.manage'] },
      { label: 'Returns', icon: 'list', route: '/pharmacy/returns', permissions: ['pharmacy.return'] },
      { label: 'Dispense', icon: 'pharmacy', route: '/pharmacy/dispense', permissions: ['pharmacy.dispense'] },
      { label: 'Settings', icon: 'settings', route: '/pharmacy/settings', permissions: ['pharmacy.settings.manage'] },
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
      { label: 'Requests', icon: 'receipt', route: '/inventory/requests', permissions: ['inventory.purchase'] },
      { label: 'Reports', icon: 'reporting', route: '/inventory/reports', permissions: ['inventory.reports.view'] },
    ],
  },
    ],
  },
  {
    label: 'People & Finance',
    items: [
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
      { label: 'Documents', icon: 'receipt', route: '/hr/documents', permissions: ['hr.view'] },
      { label: 'Payroll', icon: 'billing', route: '/hr/payroll', permissions: ['payroll.view'] },
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
      { label: 'Ledger', icon: 'list', route: '/accounting/ledger', permissions: ['accounting.view'] },
      { label: 'Vouchers', icon: 'receipt', route: '/accounting/vouchers', permissions: ['accounting.journal.post'] },
      { label: 'Collection', icon: 'billing', route: '/accounting/collections', permissions: ['accounting.view'] },
      { label: 'Receivables', icon: 'receipt', route: '/accounting/receivables', permissions: ['accounting.view'] },
      { label: 'Payables', icon: 'receipt', route: '/accounting/payables', permissions: ['accounting.view'] },
      { label: 'Expenses', icon: 'service', route: '/accounting/expenses', permissions: ['accounting.view'] },
      { label: 'Payroll', icon: 'users', route: '/accounting/payroll', permissions: ['accounting.view'] },
      { label: 'Cash/Bank', icon: 'accounting', route: '/accounting/cash-closing', permissions: ['accounting.view'] },
      { label: 'Reports', icon: 'reporting', route: '/accounting/reports', permissions: ['reporting.financial.view'] },
    ],
  },
    ],
  },
  {
    label: 'Management',
    items: [
      {
        label: 'Reporting',
        icon: 'reporting',
        permissions: ['reporting.view'],
        children: [
          { label: 'Report Library', icon: 'reporting', route: '/reporting/library', permissions: ['reporting.view'] },
          { label: 'Financial Summary', icon: 'accounting', route: '/reporting/finance', permissions: ['reporting.financial.view'] },
          { label: 'Clinical Operations', icon: 'dashboard', route: '/reporting/clinical', permissions: ['reporting.view'] },
          { label: 'Doctor Referrals', icon: 'users', route: '/reporting/doctor-referrals', permissions: ['reporting.financial.view'] },
        ],
      },
  {
    label: 'Administration',
    icon: 'admin',
    permissions: ['settings.user.manage'],
    children: [
      { label: 'Configuration', icon: 'settings', route: '/configuration', permissions: ['settings.configuration.manage'] },
      { label: 'Queue Center', icon: 'list', route: '/queue', permissions: ['queue.view'] },
      { label: 'Notifications', icon: 'list', route: '/notifications', permissions: ['notification.view'] },
      { label: 'Notification Settings', icon: 'settings', route: '/notifications/settings', permissions: ['notification.configure'] },
      { label: 'AI Assistant', icon: 'settings', route: '/ai/settings', permissions: ['ai.assistant.configure'] },
      { label: 'Barcode & QR', icon: 'settings', route: '/scanner/settings', permissions: ['scanner.settings.manage'] },
      { label: 'User Manual', icon: 'settings', route: '/manual', permissions: ['dashboard.view'] },
      { label: 'Users', icon: 'users', route: '/admin/users', permissions: ['settings.user.manage'] },
      { label: 'Roles', icon: 'shield', route: '/admin/roles', permissions: ['settings.role.manage'] },
    ],
  },
    ],
  },
];

export const menuConfig: MenuItem[] = menuSections.flatMap((section) => section.items);
