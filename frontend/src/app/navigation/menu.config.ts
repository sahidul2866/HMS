export interface MenuItem {
  label: string;
  route: string;
  permissions: string[];
}

export const menuConfig: MenuItem[] = [
  { label: 'Dashboard', route: '/dashboard', permissions: ['dashboard.view'] },
  { label: 'Patients', route: '/patients', permissions: ['patient.view'] },
  { label: 'New Patient', route: '/patients/new', permissions: ['patient.create'] },
  { label: 'Pharmacy Dispense', route: '/pharmacy/dispense', permissions: ['pharmacy.dispense'] },
  { label: 'Accounting Journal', route: '/accounting/journal', permissions: ['accounting.journal.post'] },
  { label: 'Users', route: '/admin/users', permissions: ['settings.user.manage'] },
  { label: 'Roles', route: '/admin/roles', permissions: ['settings.role.manage'] },
];

