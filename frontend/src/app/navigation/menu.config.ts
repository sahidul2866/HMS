export interface MenuItem {
  label: string;
  permissions: string[];
  route?: string;
  children?: MenuItem[];
}

export const menuConfig: MenuItem[] = [
  { label: 'Dashboard', route: '/dashboard', permissions: ['dashboard.view'] },
  {
    label: 'Patients',
    permissions: ['patient.view'],
    children: [
      { label: 'Patient List', route: '/patients', permissions: ['patient.view'] },
      { label: 'New Patient', route: '/patients/new', permissions: ['patient.create'] },
    ],
  },
  {
    label: 'Billing',
    permissions: ['billing.view'],
    children: [
      { label: 'Billing Desk', route: '/billing', permissions: ['billing.invoice.create'] },
      { label: 'Billing Services', route: '/billing/services', permissions: ['billing.service.manage'] },
      { label: 'Referred Doctors', route: '/billing/doctors', permissions: ['billing.doctor.manage'] },
    ],
  },
  { label: 'Laboratory', route: '/laboratory', permissions: ['laboratory.view'] },
  { label: 'Radiology', route: '/radiology', permissions: ['radiology.view'] },
  { label: 'Reporting', route: '/reporting', permissions: ['reporting.view'] },
  { label: 'Pharmacy Dispense', route: '/pharmacy/dispense', permissions: ['pharmacy.dispense'] },
  { label: 'Accounting Journal', route: '/accounting/journal', permissions: ['accounting.journal.post'] },
  {
    label: 'Administration',
    permissions: ['settings.user.manage'],
    children: [
      { label: 'Users', route: '/admin/users', permissions: ['settings.user.manage'] },
      { label: 'Roles', route: '/admin/roles', permissions: ['settings.role.manage'] },
    ],
  },
];
