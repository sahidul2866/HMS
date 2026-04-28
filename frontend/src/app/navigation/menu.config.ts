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
  { label: 'Accounting', icon: 'accounting', route: '/accounting/journal', permissions: ['accounting.journal.post'] },
  {
    label: 'Administration',
    icon: 'admin',
    permissions: ['settings.user.manage'],
    children: [
      { label: 'Users', icon: 'users', route: '/admin/users', permissions: ['settings.user.manage'] },
      { label: 'Roles', icon: 'shield', route: '/admin/roles', permissions: ['settings.role.manage'] },
    ],
  },
];
