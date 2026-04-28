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
import { PatientDetailComponent } from './features/patients/pages/patient-detail/patient-detail.component';
import { BillingCreateComponent } from './features/billing/pages/billing-create/billing-create.component';
import { BillingDeskComponent } from './features/billing/pages/billing-desk/billing-desk.component';
import { BillingSettingsComponent } from './features/billing/pages/billing-settings/billing-settings.component';
import { BillingServicesComponent } from './features/billing/pages/billing-services/billing-services.component';
import { AppointmentCreateComponent } from './features/appointments/pages/appointment-create/appointment-create.component';
import { AppointmentsOverviewComponent } from './features/appointments/pages/appointments-overview/appointments-overview.component';
import { IPDOverviewComponent } from './features/ipd/pages/ipd-overview/ipd-overview.component';
import { IPDAdmitComponent } from './features/ipd/pages/ipd-admit/ipd-admit.component';
import { LaboratoryOverviewComponent } from './features/laboratory/pages/laboratory-overview/laboratory-overview.component';
import { LaboratoryWorkbenchComponent } from './features/laboratory/pages/laboratory-workbench/laboratory-workbench.component';
import { OPDOverviewComponent } from './features/opd/pages/opd-overview/opd-overview.component';
import { OPDRegisterComponent } from './features/opd/pages/opd-register/opd-register.component';
import { OPDSettingsComponent } from './features/opd/pages/opd-settings/opd-settings.component';
import { RadiologyOverviewComponent } from './features/radiology/pages/radiology-overview/radiology-overview.component';
import { RadiologyWorkbenchComponent } from './features/radiology/pages/radiology-workbench/radiology-workbench.component';
import { ReportingOverviewComponent } from './features/reporting/pages/reporting-overview/reporting-overview.component';
import { PatientPortalComponent } from './features/patient-portal/pages/patient-portal/patient-portal.component';
import { PharmacyDispenseComponent } from './features/pharmacy/pages/pharmacy-dispense/pharmacy-dispense.component';
import { PharmacyOverviewComponent } from './features/pharmacy/pages/pharmacy-overview/pharmacy-overview.component';
import { PharmacySettingsComponent } from './features/pharmacy/pages/pharmacy-settings/pharmacy-settings.component';
import { PharmacyWorkbenchComponent } from './features/pharmacy/pages/pharmacy-workbench/pharmacy-workbench.component';
import { PharmacyMasterPageComponent } from './features/pharmacy/pages/pharmacy-master-page/pharmacy-master-page.component';
import { PharmacyMedicinesComponent } from './features/pharmacy/pages/pharmacy-medicines/pharmacy-medicines.component';
import { PharmacyPurchasesComponent } from './features/pharmacy/pages/pharmacy-purchases/pharmacy-purchases.component';
import { PharmacySalesEditorComponent } from './features/pharmacy/pages/pharmacy-sales-editor/pharmacy-sales-editor.component';
import { PharmacySalesListComponent } from './features/pharmacy/pages/pharmacy-sales-list/pharmacy-sales-list.component';
import { PharmacyReturnsComponent } from './features/pharmacy/pages/pharmacy-returns/pharmacy-returns.component';
import { PharmacyInvestigationSettingsComponent } from './features/diagnostics/pages/diagnostics-settings/pharmacy-investigation-settings.component';
import { PharmacyInvestigationsComponent } from './features/diagnostics/pages/diagnostics-orders/pharmacy-investigations.component';
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
        path: 'appointments/create',
        component: AppointmentCreateComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['appointment.manage'], tabLabel: 'Create Appointment' },
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
        path: 'patients/:patientId',
        component: PatientDetailComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['patient.view'], tabLabel: 'Patient Detail' },
      },
      {
        path: 'billing',
        component: BillingDeskComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['billing.invoice.create'], tabLabel: 'Billing List', billingView: 'all' },
      },
      {
        path: 'billing/due-payments',
        component: BillingDeskComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['billing.invoice.create'], tabLabel: 'Due Payment List', billingView: 'due' },
      },
      {
        path: 'billing/create',
        component: BillingCreateComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['billing.invoice.create'], tabLabel: 'Create Invoice' },
      },
      {
        path: 'billing/services',
        component: BillingServicesComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['billing.service.manage'], tabLabel: 'Billing Services' },
      },
      {
        path: 'billing/settings',
        component: BillingSettingsComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['billing.service.manage'], tabLabel: 'Billing Settings' },
      },
      {
        path: 'opd',
        component: OPDOverviewComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['opd.view'], tabLabel: 'OPD' },
      },
      {
        path: 'opd/register',
        component: OPDRegisterComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['opd.view'], tabLabel: 'Register OPD Visit' },
      },
      {
        path: 'opd/settings',
        component: OPDSettingsComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['settings.user.manage'], tabLabel: 'OPD Settings' },
      },
      {
        path: 'ipd',
        component: IPDOverviewComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['ipd.view'], tabLabel: 'IPD' },
      },
      {
        path: 'ipd/admit',
        component: IPDAdmitComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['ipd.view'], tabLabel: 'New Admission' },
      },
      {
        path: 'laboratory',
        component: LaboratoryOverviewComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['laboratory.view'], tabLabel: 'Laboratory' },
      },
      {
        path: 'laboratory/workbench/:orderId',
        component: LaboratoryWorkbenchComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['laboratory.view'], tabLabel: 'Laboratory Workbench' },
      },
      {
        path: 'radiology',
        component: RadiologyOverviewComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['radiology.view'], tabLabel: 'Radiology' },
      },
      {
        path: 'radiology/workbench/:orderId',
        component: RadiologyWorkbenchComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['radiology.view'], tabLabel: 'Radiology Workbench' },
      },
      {
        path: 'reporting',
        component: ReportingOverviewComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['reporting.view'], tabLabel: 'Reporting' },
      },
      {
        path: 'pharmacy',
        component: PharmacyOverviewComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['pharmacy.view'], tabLabel: 'Pharmacy' },
      },
      {
        path: 'pharmacy/dispense',
        component: PharmacyDispenseComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['pharmacy.dispense'], tabLabel: 'Pharmacy Dispense' },
      },
      {
        path: 'pharmacy/dispense/workbench',
        component: PharmacyWorkbenchComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['pharmacy.dispense'], tabLabel: 'Pharmacy Workbench' },
      },
      {
        path: 'pharmacy/settings',
        component: PharmacySettingsComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['pharmacy.view'], tabLabel: 'Pharmacy Settings' },
      },
      {
        path: 'pharmacy/medicine-types',
        component: PharmacyMasterPageComponent,
        canActivate: [permissionGuard],
        data: {
          permissions: ['pharmacy.view'],
          tabLabel: 'Medicine Type',
          config: {
            entityKey: 'medicine-types',
            title: 'Medicine Type',
            subtitle: 'Maintain core medicine type master data for classification and filtering.',
            eyebrow: 'Pharmacy Master',
            createLabel: 'Create Medicine Type',
            searchPlaceholder: 'Search medicine type',
            fields: [
              { key: 'name', label: 'Name', type: 'text', required: true },
              { key: 'description', label: 'Description', type: 'textarea' },
            ],
            columns: [
              { key: 'name', label: 'Name' },
              { key: 'description', label: 'Description' },
            ],
          },
        },
      },
      {
        path: 'pharmacy/generics',
        component: PharmacyMasterPageComponent,
        canActivate: [permissionGuard],
        data: {
          permissions: ['pharmacy.view'],
          tabLabel: 'Generic Information',
          config: {
            entityKey: 'generics',
            title: 'Generic Information',
            subtitle: 'Maintain generic names used by medicine records and downstream pharmacy lookups.',
            eyebrow: 'Pharmacy Master',
            createLabel: 'Create Generic',
            searchPlaceholder: 'Search generic',
            fields: [
              { key: 'name', label: 'Name', type: 'text', required: true },
              { key: 'description', label: 'Description', type: 'textarea' },
            ],
            columns: [
              { key: 'name', label: 'Name' },
              { key: 'description', label: 'Description' },
            ],
          },
        },
      },
      {
        path: 'pharmacy/companies',
        component: PharmacyMasterPageComponent,
        canActivate: [permissionGuard],
        data: {
          permissions: ['pharmacy.view'],
          tabLabel: 'Medicine Company Info',
          config: {
            entityKey: 'companies',
            title: 'Medicine Company Info',
            subtitle: 'Track manufacturer and supplier-facing company information used by medicine catalog records.',
            eyebrow: 'Pharmacy Master',
            createLabel: 'Create Company',
            searchPlaceholder: 'Search company, contact, phone',
            fields: [
              { key: 'name', label: 'Company Name', type: 'text', required: true },
              { key: 'contact_person', label: 'Contact Person', type: 'text' },
              { key: 'phone', label: 'Phone', type: 'text' },
              { key: 'email', label: 'Email', type: 'email' },
              { key: 'address', label: 'Address', type: 'textarea' },
              { key: 'note', label: 'Note', type: 'textarea' },
            ],
            columns: [
              { key: 'name', label: 'Name' },
              { key: 'contact_person', label: 'Contact' },
              { key: 'phone', label: 'Phone' },
              { key: 'email', label: 'Email' },
            ],
          },
        },
      },
      {
        path: 'pharmacy/customers',
        component: PharmacyMasterPageComponent,
        canActivate: [permissionGuard],
        data: {
          permissions: ['pharmacy.view'],
          tabLabel: 'Customer Information',
          config: {
            entityKey: 'customers',
            title: 'Customer Information',
            subtitle: 'Maintain pharmacy walk-in customer and linked patient records for sales and investigation intake.',
            eyebrow: 'Pharmacy Master',
            createLabel: 'Create Customer',
            searchPlaceholder: 'Search customer name, number, phone',
            fields: [
              { key: 'name', label: 'Customer Name', type: 'text', required: true },
              { key: 'phone', label: 'Phone', type: 'text' },
              { key: 'email', label: 'Email', type: 'email' },
              { key: 'address', label: 'Address', type: 'textarea' },
              { key: 'note', label: 'Note', type: 'textarea' },
            ],
            columns: [
              { key: 'customer_number', label: 'Customer No' },
              { key: 'name', label: 'Name' },
              { key: 'phone', label: 'Phone' },
              { key: 'patient_number', label: 'Patient' },
            ],
          },
        },
      },
      {
        path: 'pharmacy/medicines',
        component: PharmacyMedicinesComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['pharmacy.view'], tabLabel: 'Medicine Information' },
      },
      {
        path: 'pharmacy/purchases',
        component: PharmacyPurchasesComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['pharmacy.view'], tabLabel: 'Purchase History' },
      },
      {
        path: 'pharmacy/sales',
        component: PharmacySalesEditorComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['pharmacy.view'], tabLabel: 'Medicine Sales' },
      },
      {
        path: 'pharmacy/sales/list',
        component: PharmacySalesListComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['pharmacy.view'], tabLabel: 'Medicine Sales List' },
      },
      {
        path: 'pharmacy/returns',
        component: PharmacyReturnsComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['pharmacy.view'], tabLabel: 'Medicine Return List' },
      },
      {
        path: 'diagnostics/settings',
        component: PharmacyInvestigationSettingsComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['laboratory.view'], tabLabel: 'Diagnostics Settings' },
      },
      {
        path: 'diagnostics/orders',
        component: PharmacyInvestigationsComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['laboratory.view'], tabLabel: 'Diagnostics Orders' },
      },
      {
        path: 'pharmacy/investigation-settings',
        redirectTo: 'diagnostics/settings',
        pathMatch: 'full',
      },
      {
        path: 'pharmacy/investigations',
        redirectTo: 'diagnostics/orders',
        pathMatch: 'full',
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
