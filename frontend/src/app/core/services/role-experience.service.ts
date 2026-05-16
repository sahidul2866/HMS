import { Injectable, inject } from '@angular/core';

import { SessionService } from './session.service';

export interface RoleAction {
  label: string;
  detail: string;
  route: string;
  permissions: string[];
  tone?: 'primary' | 'warning' | 'danger' | 'success' | 'info';
  shortcut?: string;
}

export interface RoleMetric {
  label: string;
  value: string;
  detail: string;
  route: string;
  permissions: string[];
  tone?: string;
}

export interface RoleExperience {
  code: string;
  label: string;
  homeTitle: string;
  homeSubtitle: string;
  focus: string[];
  actions: RoleAction[];
  metrics: RoleMetric[];
  shortcuts: Array<{ key: string; label: string; route?: string; permissions?: string[] }>;
}

@Injectable({ providedIn: 'root' })
export class RoleExperienceService {
  private readonly session = inject(SessionService);

  roleCodes(): string[] {
    return this.session.snapshot.user?.roles?.map((role) => role.code) ?? [];
  }

  primaryExperience(): RoleExperience {
    const roles = this.roleCodes();
    return ROLE_PRIORITY.map((code) => ROLE_EXPERIENCES[code]).find((experience) => experience && roles.includes(experience.code)) ?? ROLE_EXPERIENCES['STAFF'];
  }

  visibleActions(experience = this.primaryExperience()): RoleAction[] {
    return experience.actions.filter((action) => this.session.hasAnyPermission(action.permissions));
  }

  visibleMetrics(experience = this.primaryExperience()): RoleMetric[] {
    return experience.metrics.filter((metric) => this.session.hasAnyPermission(metric.permissions));
  }

  visibleShortcuts(experience = this.primaryExperience()): Array<{ key: string; label: string; route?: string }> {
    return experience.shortcuts.filter((shortcut) => !shortcut.permissions || this.session.hasAnyPermission(shortcut.permissions));
  }

  canSeeManagementAnalytics(): boolean {
    return this.session.hasAnyPermission(['admin.manage_users', 'reporting.financial.view', 'accounting.dashboard.view', 'settings.configuration.manage']);
  }

  routeForShortcut(key: string): string | null {
    const shortcut = this.visibleShortcuts().find((item) => item.key.toLowerCase() === key.toLowerCase());
    return shortcut?.route ?? null;
  }
}

const ROLE_PRIORITY = [
  'SUPER_ADMIN',
  'ADMIN',
  'MANAGEMENT',
  'DOCTOR',
  'DOCTOR_ASSISTANT',
  'NURSE',
  'RECEPTIONIST',
  'PHARMACIST',
  'LAB_TECHNICIAN',
  'RADIOLOGY_TECHNICIAN',
  'BILLING_STAFF',
  'ACCOUNTANT',
  'INVENTORY_MANAGER',
  'BLOOD_BANK_OFFICER',
  'HR_MANAGER',
  'PAYROLL_OFFICER',
  'OT_MANAGER',
  'SURGEON',
  'ANESTHETIST',
  'OT_NURSE',
  'EMPLOYEE',
];

const ROLE_EXPERIENCES: Record<string, RoleExperience> = {
  SUPER_ADMIN: adminExperience('SUPER_ADMIN', 'Super Admin'),
  ADMIN: adminExperience('ADMIN', 'Admin'),
  MANAGEMENT: {
    code: 'MANAGEMENT',
    label: 'Management',
    homeTitle: 'Management Dashboard',
    homeSubtitle: 'Hospital-wide performance, queues, approvals, finance, occupancy, and operational risk.',
    focus: ['Executive summary', 'Approvals', 'Revenue and dues', 'Occupancy', 'Queue performance'],
    actions: [
      action('Hospital Summary', 'Open reporting library', '/reporting/library', ['reporting.view'], 'primary', 'Alt+1'),
      action('Financial Summary', 'Revenue, dues, and cash', '/reporting/finance', ['reporting.financial.view'], 'info', 'Alt+2'),
      action('Queues', 'Monitor patient flow', '/queue', ['queue.view'], 'warning', 'Alt+Q'),
      action('Accounting', 'Approvals and cash/bank', '/accounting', ['accounting.view'], 'info', 'Alt+4'),
    ],
    metrics: [
      metric('Appointments', "Today's appointments", '/appointments', ['appointment.view']),
      metric('Emergency', 'Active ER load', '/er', ['er.view'], 'danger'),
      metric('Revenue', 'Collections and dues', '/accounting', ['accounting.view']),
      metric('Beds', 'IPD occupancy', '/ipd', ['ipd.view']),
    ],
    shortcuts: shortcuts(['Alt+1', 'Reports', '/reporting'], ['Alt+Q', 'Queue center', '/queue'], ['Alt+4', 'Accounting', '/accounting']),
  },
  DOCTOR: {
    code: 'DOCTOR',
    label: 'Doctor',
    homeTitle: 'Doctor Dashboard',
    homeSubtitle: 'Consultations, assigned patients, results, clinical orders, prescriptions, and discharge work.',
    focus: ['Today appointments', 'OPD/IPD patients', 'Results ready', 'Clinical orders', 'Critical alerts'],
    actions: [
      action('OPD Queue', 'Open consultation queue', '/opd/visits', ['opd.view'], 'primary', 'Alt+3'),
      action('New Prescription', 'Open OPD workspace', '/opd', ['opd.prescribe'], 'success', 'Ctrl+S'),
      action('Order Tests', 'Create diagnostics order', '/diagnostics/orders', ['diagnostics.order.manage'], 'info', 'Alt+6'),
      action('IPD Admissions', 'Review admitted patients', '/ipd/admissions', ['ipd.view'], 'warning', 'Alt+4'),
      action('Emergency', 'Review ER cases', '/er', ['er.view'], 'danger', 'Alt+5'),
    ],
    metrics: [
      metric('Appointments', 'Today appointments', '/appointments', ['appointment.view']),
      metric('Pending OPD', 'Consultation queue', '/opd/visits', ['opd.view']),
      metric('IPD Patients', 'Assigned inpatients', '/ipd/admissions', ['ipd.view']),
      metric('Results', 'Lab/radiology worklists', '/laboratory', ['laboratory.view', 'radiology.view']),
    ],
    shortcuts: shortcuts(['Alt+3', 'OPD visits', '/opd/visits'], ['Alt+4', 'IPD admissions', '/ipd/admissions'], ['Alt+6', 'Lab results', '/laboratory'], ['Alt+7', 'Radiology', '/radiology']),
  },
  DOCTOR_ASSISTANT: {
    code: 'DOCTOR_ASSISTANT',
    label: 'Doctor Assistant',
    homeTitle: 'Doctor Assistant Dashboard',
    homeSubtitle: 'Patient preparation, vitals, queue support, investigation preparation, and documents.',
    focus: ['Doctor queue', 'Vitals collection', 'Patient documents', 'Investigation prep', 'Follow-up support'],
    actions: [
      action('Doctor Queue', 'Prepare waiting patients', '/opd/visits', ['opd.queue.view'], 'primary', 'Alt+3'),
      action('Register Visit', 'Create OPD visit', '/opd/register', ['opd.visit.create'], 'success', 'Alt+2'),
      action('Appointments', 'Coordinate follow-ups', '/appointments', ['appointment.view'], 'info', 'Alt+4'),
      action('Patients', 'Patient documents', '/patients', ['patient.view'], 'info', 'Alt+5'),
    ],
    metrics: [
      metric('Queue', 'Patients waiting', '/opd/visits', ['opd.queue.view']),
      metric('Appointments', 'Today schedule', '/appointments', ['appointment.view']),
      metric('Patients', 'Document support', '/patients', ['patient.view']),
      metric('Vitals', 'Basic preparation', '/opd/visits', ['opd.visit.edit']),
    ],
    shortcuts: shortcuts(['Alt+3', 'Doctor queue', '/opd/visits'], ['Alt+2', 'Register OPD', '/opd/register'], ['Alt+5', 'Patients', '/patients']),
  },
  NURSE: {
    code: 'NURSE',
    label: 'Nurse',
    homeTitle: 'Nursing Dashboard',
    homeSubtitle: 'Assigned patients, medicine and vitals due, nursing notes, handover, and ward tasks.',
    focus: ['Assigned patients', 'Medicine due', 'Vitals due', 'Handover', 'Abnormal alerts'],
    actions: [
      action('IPD Patients', 'Ward and bedside work', '/ipd/admissions', ['ipd.view'], 'primary', 'Alt+4'),
      action('Nursing Notes', 'Vitals and nursing updates', '/ipd', ['ipd.nursing_note.create'], 'success', 'Alt+N'),
      action('Medication Due', 'Administer medicines', '/ipd', ['ipd.medication.administer'], 'warning', 'Alt+M'),
      action('Handover', 'Create or acknowledge handover', '/ipd', ['ipd.handover.create', 'ipd.handover.acknowledge'], 'info', 'Alt+H'),
      action('Emergency', 'Triage and status', '/er', ['er.triage.manage'], 'danger', 'Alt+5'),
    ],
    metrics: [
      metric('Assigned Patients', 'Ward responsibilities', '/ipd/admissions', ['ipd.view']),
      metric('Vitals Due', 'Pending nursing observations', '/ipd', ['ipd.nursing_note.create']),
      metric('Medicine Due', 'Administration queue', '/ipd', ['ipd.medication.administer']),
      metric('Handover', 'Pending acknowledgements', '/ipd', ['ipd.handover.acknowledge']),
    ],
    shortcuts: shortcuts(['Alt+4', 'IPD patients', '/ipd/admissions'], ['Alt+N', 'Nursing notes', '/ipd'], ['Alt+M', 'Medication', '/ipd'], ['Alt+H', 'Handover', '/ipd']),
  },
  RECEPTIONIST: {
    code: 'RECEPTIONIST',
    label: 'Receptionist',
    homeTitle: 'Front Desk Dashboard',
    homeSubtitle: 'Registration, appointment check-in, queue tokens, patient cards, and front-desk tasks.',
    focus: ['Registration', 'Appointment check-in', 'Queue tokens', 'Patient cards', 'Reschedule'],
    actions: [
      action('New Patient', 'Register demographics', '/patients/new', ['patient.create'], 'primary', 'Alt+2'),
      action('Appointments', 'Check in and reschedule', '/appointments', ['appointment.view'], 'info', 'Alt+3'),
      action('New Appointment', 'Book visit', '/appointments/create', ['appointment.book'], 'success', 'Alt+4'),
      action('Queue Center', 'Generate and manage tokens', '/queue', ['queue.view'], 'warning', 'Alt+Q'),
      action('Patient Cards', 'Print ID cards', '/patients', ['patient.id_card.print'], 'info', 'Alt+5'),
    ],
    metrics: [
      metric('Check-ins', 'Appointments today', '/appointments', ['appointment.view']),
      metric('New Patients', 'Registration work', '/patients/new', ['patient.create']),
      metric('Queue', 'Front desk tokens', '/queue', ['queue.view']),
      metric('Cards', 'ID card printing', '/patients', ['patient.id_card.print']),
    ],
    shortcuts: shortcuts(['Alt+2', 'New patient', '/patients/new'], ['Alt+3', 'Appointments', '/appointments'], ['Alt+Q', 'Queue center', '/queue']),
  },
  PHARMACIST: queueExperience('PHARMACIST', 'Pharmacist', 'Pharmacy Dashboard', 'Pending prescriptions, dispensing, stock, returns, labels, and medicine safety.', '/pharmacy/dispense', 'pharmacy.dispense'),
  LAB_TECHNICIAN: queueExperience('LAB_TECHNICIAN', 'Lab Staff', 'Laboratory Dashboard', 'Sample collection, received samples, result entry, verification, and critical lab alerts.', '/laboratory', 'laboratory.view'),
  RADIOLOGY_TECHNICIAN: queueExperience('RADIOLOGY_TECHNICIAN', 'Radiology Staff', 'Radiology Dashboard', 'Imaging queue, report upload, verification, PACS/image review, and completed reports.', '/radiology', 'radiology.view'),
  BILLING_STAFF: queueExperience('BILLING_STAFF', 'Billing Staff', 'Billing Dashboard', 'Billing queue, invoices, payments, refunds, dues, and discharge clearance.', '/billing/list', 'billing.view'),
  ACCOUNTANT: queueExperience('ACCOUNTANT', 'Accountant', 'Accounting Dashboard', 'Vouchers, receivables, payables, expenses, cash/bank, and financial reports.', '/accounting', 'accounting.view'),
  INVENTORY_MANAGER: queueExperience('INVENTORY_MANAGER', 'Inventory Staff', 'Inventory Dashboard', 'Low stock, requisitions, transfers, receiving, expiry risk, and stock adjustments.', '/inventory', 'inventory.view'),
  BLOOD_BANK_OFFICER: queueExperience('BLOOD_BANK_OFFICER', 'Blood Bank Staff', 'Blood Bank Dashboard', 'Requests, samples, crossmatch, issue, emergency stock, and near-expiry blood units.', '/blood-bank/dashboard', 'blood_bank.view'),
  HR_MANAGER: queueExperience('HR_MANAGER', 'HR Staff', 'HR Dashboard', 'Employee records, attendance, leave approvals, rosters, documents, and HR reports.', '/hr', 'hr.view'),
  PAYROLL_OFFICER: queueExperience('PAYROLL_OFFICER', 'Payroll Staff', 'Payroll Dashboard', 'Salary structures, payroll runs, exceptions, payslips, and payroll reports.', '/hr/payroll', 'payroll.view'),
  OT_MANAGER: queueExperience('OT_MANAGER', 'OT Manager', 'Operation Theatre Dashboard', 'Bookings, schedules, rooms, checklists, surgery workflow, recovery, and OT reports.', '/ot', 'ot.view'),
  SURGEON: queueExperience('SURGEON', 'Surgeon', 'Surgeon Dashboard', 'Surgery bookings, operative notes, case sheets, recovery handoff, and OT reports.', '/ot', 'ot.view'),
  ANESTHETIST: queueExperience('ANESTHETIST', 'Anesthetist', 'Anesthesia Dashboard', 'Anesthesia assessment, records, sign-off, case review, and OT reports.', '/ot/anesthesia', 'ot.anesthesia.manage'),
  OT_NURSE: queueExperience('OT_NURSE', 'OT Nurse', 'OT Nursing Dashboard', 'Pre-op checklist, recovery, surgery workflow, and OT patient handover.', '/ot/checklist', 'ot.preop.manage'),
  EMPLOYEE: queueExperience('EMPLOYEE', 'Employee', 'Employee Dashboard', 'Self-service HR, leave, documents, and assigned tasks.', '/hr/leave', 'hr.self_service'),
  STAFF: queueExperience('STAFF', 'Staff', 'Staff Dashboard', 'Your permitted hospital modules, tasks, queues, and notifications.', '/dashboard', 'dashboard.view'),
};

function action(label: string, detail: string, route: string, permissions: string[], tone?: RoleAction['tone'], shortcut?: string): RoleAction {
  return { label, detail, route, permissions, tone, shortcut };
}

function metric(label: string, detail: string, route: string, permissions: string[], tone = 'info'): RoleMetric {
  return { label, value: '-', detail, route, permissions, tone };
}

function shortcuts(...items: Array<[string, string, string?]>): Array<{ key: string; label: string; route?: string; permissions?: string[] }> {
  return items.map(([key, label, route]) => ({ key, label, route }));
}

function adminExperience(code: string, label: string): RoleExperience {
  return {
    code,
    label,
    homeTitle: `${label} Dashboard`,
    homeSubtitle: 'Users, roles, permissions, configuration, audit, security alerts, and module settings.',
    focus: ['User management', 'Roles and permissions', 'Configuration', 'Audit', 'Security'],
    actions: [
      action('Users', 'Create and manage users', '/admin/users', ['settings.user.manage'], 'primary', 'Alt+U'),
      action('Roles', 'Permission matrix', '/admin/roles', ['settings.role.manage'], 'warning', 'Alt+R'),
      action('Configuration', 'Hospital setup', '/configuration', ['settings.configuration.manage'], 'info', 'Alt+C'),
      action('Notifications', 'Rules and alerts', '/notifications/settings', ['notification.configure'], 'info', 'Alt+N'),
      action('AI Settings', 'Assistant behavior', '/ai/settings', ['ai.assistant.configure'], 'info', 'Alt+A'),
    ],
    metrics: [
      metric('Users', 'Active accounts and roles', '/admin/users', ['settings.user.manage']),
      metric('Roles', 'Permission groups', '/admin/roles', ['settings.role.manage']),
      metric('Configuration', 'Module settings', '/configuration', ['settings.configuration.manage']),
      metric('Audit', 'System accountability', '/reporting', ['audit.view', 'reporting.view']),
    ],
    shortcuts: shortcuts(['Alt+U', 'Users', '/admin/users'], ['Alt+R', 'Roles', '/admin/roles'], ['Alt+C', 'Configuration', '/configuration'], ['Alt+N', 'Notifications', '/notifications']),
  };
}

function queueExperience(code: string, label: string, homeTitle: string, homeSubtitle: string, route: string, permission: string): RoleExperience {
  return {
    code,
    label,
    homeTitle,
    homeSubtitle,
    focus: ['Work queue', 'Pending tasks', 'Approvals', 'Reports', 'Notifications'],
    actions: [
      action('Open Work Queue', 'Continue assigned work', route, [permission], 'primary', 'Alt+1'),
      action('Queue Center', 'Role queue monitoring', '/queue', ['queue.view'], 'warning', 'Alt+Q'),
      action('Notifications', 'Action alerts', '/notifications', ['notification.view'], 'info', 'Alt+N'),
      action('Reports', 'Module reporting', '/reporting', ['reporting.view'], 'info', 'Alt+R'),
    ],
    metrics: [
      metric('Pending', 'Items waiting', route, [permission]),
      metric('In Progress', 'Active work', route, [permission]),
      metric('Alerts', 'Action notifications', '/notifications', ['notification.view']),
      metric('Queue', 'Operational queue', '/queue', ['queue.view']),
    ],
    shortcuts: shortcuts(['Alt+1', 'Work queue', route], ['Alt+Q', 'Queue center', '/queue'], ['Alt+N', 'Notifications', '/notifications']),
  };
}
