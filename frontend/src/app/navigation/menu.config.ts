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
      { label: 'Patient List', icon: 'list', route: '/patients', permissions: ['patient.view'] },
      { label: 'New Patient', icon: 'plus-user', route: '/patients/new', permissions: ['patient.create'] },
    ],
  },
  {
    label: 'Billing',
    icon: 'billing',
    permissions: ['billing.view'],
    children: [
      { label: 'Billing Desk', icon: 'receipt', route: '/billing', permissions: ['billing.invoice.create'] },
      { label: 'New Invoice', icon: 'plus-user', route: '/billing/create', permissions: ['billing.invoice.create'] },
      { label: 'Billing Services', icon: 'service', route: '/billing/services', permissions: ['billing.service.manage'] },
    ],
  },
  { label: 'OPD', icon: 'opd', route: '/opd', permissions: ['opd.view'] },
  { label: 'IPD', icon: 'ipd', route: '/ipd', permissions: ['ipd.view'] },
  { label: 'Laboratory', icon: 'lab', route: '/laboratory', permissions: ['laboratory.view'] },
  { label: 'Radiology', icon: 'radiology', route: '/radiology', permissions: ['radiology.view'] },
  { label: 'Reporting', icon: 'reporting', route: '/reporting', permissions: ['reporting.view'] },
  { label: 'Pharmacy Dispense', icon: 'pharmacy', route: '/pharmacy/dispense', permissions: ['pharmacy.dispense'] },
  { label: 'Accounting Journal', icon: 'accounting', route: '/accounting/journal', permissions: ['accounting.journal.post'] },
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
