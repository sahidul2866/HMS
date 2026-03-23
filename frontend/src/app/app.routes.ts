import { Routes } from '@angular/router';

import { authGuard } from './core/guards/auth.guard';
import { permissionGuard } from './core/guards/permission.guard';
import { AuthLayoutComponent } from './layouts/auth-layout/auth-layout.component';
import { AppLayoutComponent } from './layouts/app-layout/app-layout.component';
import { LoginComponent } from './features/auth/pages/login/login.component';
import { PatientRegisterComponent } from './features/auth/pages/patient-register/patient-register.component';
import { DashboardComponent } from './features/dashboard/pages/dashboard/dashboard.component';
import { PatientListComponent } from './features/patients/pages/patient-list/patient-list.component';
import { PatientCreateComponent } from './features/patients/pages/patient-create/patient-create.component';
import { BillingDeskComponent } from './features/billing/pages/billing-desk/billing-desk.component';
import { BillingServicesComponent } from './features/billing/pages/billing-services/billing-services.component';
import { AppointmentsOverviewComponent } from './features/appointments/pages/appointments-overview/appointments-overview.component';
import { IPDOverviewComponent } from './features/ipd/pages/ipd-overview/ipd-overview.component';
import { LaboratoryOverviewComponent } from './features/laboratory/pages/laboratory-overview/laboratory-overview.component';
import { OPDOverviewComponent } from './features/opd/pages/opd-overview/opd-overview.component';
import { RadiologyOverviewComponent } from './features/radiology/pages/radiology-overview/radiology-overview.component';
import { ReportingOverviewComponent } from './features/reporting/pages/reporting-overview/reporting-overview.component';
import { PatientPortalComponent } from './features/patient-portal/pages/patient-portal/patient-portal.component';
import { PharmacyDispenseComponent } from './features/pharmacy/pages/pharmacy-dispense/pharmacy-dispense.component';
import { AccountingJournalComponent } from './features/accounting/pages/accounting-journal/accounting-journal.component';
import { UserManagementComponent } from './features/admin/pages/user-management/user-management.component';
import { RoleManagementComponent } from './features/admin/pages/role-management/role-management.component';

export const appRoutes: Routes = [
  {
    path: 'auth',
    component: AuthLayoutComponent,
    children: [
      { path: 'login', component: LoginComponent, data: { tabLabel: 'Login' } },
      { path: 'patient-register', component: PatientRegisterComponent, data: { tabLabel: 'Patient Register' } },
    ],
  },
  {
    path: '',
    component: AppLayoutComponent,
    canActivate: [authGuard],
    children: [
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
      {
        path: 'dashboard',
        component: DashboardComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['dashboard.view'], tabLabel: 'Dashboard' },
      },
      {
        path: 'portal',
        component: PatientPortalComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['patient.portal.view'], tabLabel: 'My Portal' },
      },
      {
        path: 'appointments',
        component: AppointmentsOverviewComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['appointment.view'], tabLabel: 'Appointments' },
      },
      {
        path: 'patients',
        component: PatientListComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['patient.view'], tabLabel: 'Patients' },
      },
      {
        path: 'patients/new',
        component: PatientCreateComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['patient.create'], tabLabel: 'New Patient' },
      },
      {
        path: 'billing',
        component: BillingDeskComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['billing.invoice.create'], tabLabel: 'Billing Desk' },
      },
      {
        path: 'billing/services',
        component: BillingServicesComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['billing.service.manage'], tabLabel: 'Billing Services' },
      },
      {
        path: 'opd',
        component: OPDOverviewComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['opd.view'], tabLabel: 'OPD' },
      },
      {
        path: 'ipd',
        component: IPDOverviewComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['ipd.view'], tabLabel: 'IPD' },
      },
      {
        path: 'laboratory',
        component: LaboratoryOverviewComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['laboratory.view'], tabLabel: 'Laboratory' },
      },
      {
        path: 'radiology',
        component: RadiologyOverviewComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['radiology.view'], tabLabel: 'Radiology' },
      },
      {
        path: 'reporting',
        component: ReportingOverviewComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['reporting.view'], tabLabel: 'Reporting' },
      },
      {
        path: 'pharmacy/dispense',
        component: PharmacyDispenseComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['pharmacy.dispense'], tabLabel: 'Pharmacy Dispense' },
      },
      {
        path: 'accounting/journal',
        component: AccountingJournalComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['accounting.journal.post'], tabLabel: 'Accounting Journal' },
      },
      {
        path: 'admin/users',
        component: UserManagementComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['settings.user.manage'], tabLabel: 'Users' },
      },
      {
        path: 'admin/roles',
        component: RoleManagementComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['settings.role.manage'], tabLabel: 'Roles' },
      },
    ],
  },
  { path: '**', redirectTo: '' },
];
