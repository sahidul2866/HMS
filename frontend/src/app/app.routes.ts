import { Routes } from '@angular/router';

import { authGuard } from './core/guards/auth.guard';
import { permissionGuard } from './core/guards/permission.guard';
import { unsavedChangesGuard } from './core/guards/unsaved-changes.guard';
import { AuthLayoutComponent } from './layouts/auth-layout/auth-layout.component';
import { AppLayoutComponent } from './layouts/app-layout/app-layout.component';
import { LoginComponent } from './features/auth/pages/login/login.component';
import { PatientRegisterComponent } from './features/auth/pages/patient-register/patient-register.component';
import { DashboardComponent } from './features/dashboard/pages/dashboard/dashboard.component';
import { PatientListComponent } from './features/patients/pages/patient-list/patient-list.component';
import { PatientCreateComponent } from './features/patients/pages/patient-create/patient-create.component';
import { PatientDetailComponent } from './features/patients/pages/patient-detail/patient-detail.component';
import { PatientIdCardSettingsComponent } from './features/patients/pages/patient-id-card-settings/patient-id-card-settings.component';
import { BillingCreateComponent } from './features/billing/pages/billing-create/billing-create.component';
import { BillingDeskComponent } from './features/billing/pages/billing-desk/billing-desk.component';
import { BillingOverviewComponent } from './features/billing/pages/billing-overview/billing-overview.component';
import { BillingSettingsComponent } from './features/billing/pages/billing-settings/billing-settings.component';
import { BillingServicesComponent } from './features/billing/pages/billing-services/billing-services.component';
import { BloodBankWorkspaceComponent } from './features/blood-bank/pages/blood-bank-workspace/blood-bank-workspace.component';
import { CateringWorkspaceComponent } from './features/catering/pages/catering-workspace/catering-workspace.component';
import { AppointmentCreateComponent } from './features/appointments/pages/appointment-create/appointment-create.component';
import { AppointmentsOverviewComponent } from './features/appointments/pages/appointments-overview/appointments-overview.component';
import { IPDOverviewComponent } from './features/ipd/pages/ipd-overview/ipd-overview.component';
import { IPDAdmitComponent } from './features/ipd/pages/ipd-admit/ipd-admit.component';
import { IPDSettingsComponent } from './features/ipd/pages/ipd-settings/ipd-settings.component';
import { EROverviewComponent } from './features/er/pages/er-overview/er-overview.component';
import { ERRegisterComponent } from './features/er/pages/er-register/er-register.component';
import { LaboratoryOverviewComponent } from './features/laboratory/pages/laboratory-overview/laboratory-overview.component';
import { LaboratoryWorkbenchComponent } from './features/laboratory/pages/laboratory-workbench/laboratory-workbench.component';
import { LISSimulatorComponent } from './features/lis/pages/lis-simulator/lis-simulator.component';
import { InventoryManagementComponent } from './features/inventory/pages/inventory-management/inventory-management.component';
import { OPDOverviewComponent } from './features/opd/pages/opd-overview/opd-overview.component';
import { OPDVisitListComponent } from './features/opd/pages/opd-visit-list/opd-visit-list.component';
import { OPDRegisterComponent } from './features/opd/pages/opd-register/opd-register.component';
import { OPDSettingsComponent } from './features/opd/pages/opd-settings/opd-settings.component';
import { OTManagementComponent } from './features/ot/pages/ot-management/ot-management.component';
import { RadiologyOverviewComponent } from './features/radiology/pages/radiology-overview/radiology-overview.component';
import { RadiologyWorkbenchComponent } from './features/radiology/pages/radiology-workbench/radiology-workbench.component';
import { ReportingOverviewComponent } from './features/reporting/pages/reporting-overview/reporting-overview.component';
import { PatientPortalComponent } from './features/patient-portal/pages/patient-portal/patient-portal.component';
import { PharmacyDispenseComponent } from './features/pharmacy/pages/pharmacy-dispense/pharmacy-dispense.component';
import { PharmacyOverviewComponent } from './features/pharmacy/pages/pharmacy-overview/pharmacy-overview.component';
import { PharmacySettingsComponent } from './features/pharmacy/pages/pharmacy-settings/pharmacy-settings.component';
import { PharmacyWorkbenchComponent } from './features/pharmacy/pages/pharmacy-workbench/pharmacy-workbench.component';
import { PharmacyMasterPageComponent } from './features/pharmacy/pages/pharmacy-master-page/pharmacy-master-page.component';
import { ScannerSettingsComponent } from './features/scanner/pages/scanner-settings/scanner-settings.component';
import { AiSettingsComponent } from './features/ai/pages/ai-settings/ai-settings.component';
import { ShortcutSettingsComponent } from './features/keyboard/pages/shortcut-settings/shortcut-settings.component';
import { NotificationCenterPageComponent } from './features/notifications/pages/notification-center-page/notification-center-page.component';
import { NotificationSettingsComponent } from './features/notifications/pages/notification-settings/notification-settings.component';
import { QueueWorkspaceComponent } from './features/queue/pages/queue-workspace/queue-workspace.component';
import { PharmacyMedicinesComponent } from './features/pharmacy/pages/pharmacy-medicines/pharmacy-medicines.component';
import { PharmacyPurchasesComponent } from './features/pharmacy/pages/pharmacy-purchases/pharmacy-purchases.component';
import { PharmacySalesEditorComponent } from './features/pharmacy/pages/pharmacy-sales-editor/pharmacy-sales-editor.component';
import { PharmacySalesListComponent } from './features/pharmacy/pages/pharmacy-sales-list/pharmacy-sales-list.component';
import { PharmacyReturnsComponent } from './features/pharmacy/pages/pharmacy-returns/pharmacy-returns.component';
import { PharmacyInvestigationSettingsComponent } from './features/diagnostics/pages/diagnostics-settings/pharmacy-investigation-settings.component';
import { PharmacyInvestigationsComponent } from './features/diagnostics/pages/diagnostics-orders/pharmacy-investigations.component';
import { AccountingJournalComponent } from './features/accounting/pages/accounting-journal/accounting-journal.component';
import { HRPayrollComponent } from './features/hr/pages/hr-payroll/hr-payroll.component';
import { IPDAdmissionListComponent } from './features/ipd/pages/ipd-admission-list/ipd-admission-list.component';
import { UserManagementComponent } from './features/admin/pages/user-management/user-management.component';
import { RoleManagementComponent } from './features/admin/pages/role-management/role-management.component';
import { ConfigurationWorkspaceComponent } from './features/configuration/pages/configuration-workspace/configuration-workspace.component';
import { AccountProfileComponent } from './features/profile/pages/account-profile/account-profile.component';

const bloodBankRoutes: Routes = [
  { path: 'blood-bank', redirectTo: 'blood-bank/dashboard', pathMatch: 'full' },
  { path: 'blood-bank/dashboard', component: BloodBankWorkspaceComponent, canActivate: [permissionGuard], data: { permissions: ['blood_bank.dashboard.view'], tabLabel: 'Blood Bank Dashboard', bloodBankTab: 'dashboard' } },
  { path: 'blood-bank/queue', component: BloodBankWorkspaceComponent, canActivate: [permissionGuard], data: { permissions: ['blood_bank.queue.manage'], tabLabel: 'Blood Bank Queue', bloodBankTab: 'queue' } },
  { path: 'blood-bank/donors', component: BloodBankWorkspaceComponent, canActivate: [permissionGuard], data: { permissions: ['blood_bank.view'], tabLabel: 'Blood Donors', bloodBankTab: 'donors' } },
  { path: 'blood-bank/screening', component: BloodBankWorkspaceComponent, canActivate: [permissionGuard], data: { permissions: ['blood_bank.donor.screen'], tabLabel: 'Donor Screening', bloodBankTab: 'screening' } },
  { path: 'blood-bank/collection', component: BloodBankWorkspaceComponent, canActivate: [permissionGuard], data: { permissions: ['blood_bank.collection.create'], tabLabel: 'Blood Collection', bloodBankTab: 'collection' } },
  { path: 'blood-bank/testing', component: BloodBankWorkspaceComponent, canActivate: [permissionGuard], data: { permissions: ['blood_bank.testing.update'], tabLabel: 'Blood Testing', bloodBankTab: 'testing' } },
  { path: 'blood-bank/components', component: BloodBankWorkspaceComponent, canActivate: [permissionGuard], data: { permissions: ['blood_bank.component.prepare'], tabLabel: 'Blood Components', bloodBankTab: 'components' } },
  { path: 'blood-bank/stock', component: BloodBankWorkspaceComponent, canActivate: [permissionGuard], data: { permissions: ['blood_bank.stock.view'], tabLabel: 'Blood Stock', bloodBankTab: 'stock' } },
  { path: 'blood-bank/requests', component: BloodBankWorkspaceComponent, canActivate: [permissionGuard], data: { permissions: ['blood_bank.view'], tabLabel: 'Blood Requests', bloodBankTab: 'requests' } },
  { path: 'blood-bank/crossmatch', component: BloodBankWorkspaceComponent, canActivate: [permissionGuard], data: { permissions: ['blood_bank.crossmatch.perform'], tabLabel: 'Blood Crossmatch', bloodBankTab: 'crossmatch' } },
  { path: 'blood-bank/issue', component: BloodBankWorkspaceComponent, canActivate: [permissionGuard], data: { permissions: ['blood_bank.issue'], tabLabel: 'Blood Issue', bloodBankTab: 'issue' } },
  { path: 'blood-bank/transfusion', component: BloodBankWorkspaceComponent, canActivate: [permissionGuard], data: { permissions: ['blood_bank.transfusion.update'], tabLabel: 'Blood Transfusion', bloodBankTab: 'transfusion' } },
  { path: 'blood-bank/return', component: BloodBankWorkspaceComponent, canActivate: [permissionGuard], data: { permissions: ['blood_bank.return'], tabLabel: 'Blood Return', bloodBankTab: 'return' } },
  { path: 'blood-bank/discard', component: BloodBankWorkspaceComponent, canActivate: [permissionGuard], data: { permissions: ['blood_bank.discard'], tabLabel: 'Blood Discard', bloodBankTab: 'discard' } },
  { path: 'blood-bank/reports', component: BloodBankWorkspaceComponent, canActivate: [permissionGuard], data: { permissions: ['blood_bank.report.view'], tabLabel: 'Blood Bank Reports', bloodBankTab: 'reports' } },
  { path: 'blood-bank/settings', component: BloodBankWorkspaceComponent, canActivate: [permissionGuard], data: { permissions: ['blood_bank.component.prepare'], tabLabel: 'Blood Bank Settings', bloodBankTab: 'settings' } },
];

const cateringRoutes: Routes = [
  { path: 'catering', redirectTo: 'catering/dashboard', pathMatch: 'full' },
  { path: 'catering/dashboard', component: CateringWorkspaceComponent, canActivate: [permissionGuard], data: { permissions: ['catering.dashboard.view'], tabLabel: 'Catering Dashboard', cateringTab: 'dashboard' } },
  { path: 'catering/diet-orders', component: CateringWorkspaceComponent, canActivate: [permissionGuard], data: { permissions: ['catering.view'], tabLabel: 'Patient Diet Orders', cateringTab: 'diet-orders' } },
  { path: 'catering/kitchen', component: CateringWorkspaceComponent, canActivate: [permissionGuard], data: { permissions: ['catering.kitchen_queue.view'], tabLabel: 'Kitchen Queue', cateringTab: 'kitchen' } },
  { path: 'catering/schedule', component: CateringWorkspaceComponent, canActivate: [permissionGuard], data: { permissions: ['catering.settings.manage'], tabLabel: 'Meal Schedule', cateringTab: 'schedule' } },
  { path: 'catering/delivery', component: CateringWorkspaceComponent, canActivate: [permissionGuard], data: { permissions: ['catering.meal.deliver'], tabLabel: 'Meal Delivery', cateringTab: 'delivery' } },
  { path: 'catering/staff-meals', component: CateringWorkspaceComponent, canActivate: [permissionGuard], data: { permissions: ['catering.staff_meal.manage'], tabLabel: 'Staff Meals', cateringTab: 'staff-meals' } },
  { path: 'catering/inventory', component: CateringWorkspaceComponent, canActivate: [permissionGuard], data: { permissions: ['catering.kitchen_queue.view'], tabLabel: 'Kitchen Inventory', cateringTab: 'inventory' } },
  { path: 'catering/reports', component: CateringWorkspaceComponent, canActivate: [permissionGuard], data: { permissions: ['catering.report.view'], tabLabel: 'Catering Reports', cateringTab: 'reports' } },
  { path: 'catering/settings', component: CateringWorkspaceComponent, canActivate: [permissionGuard], data: { permissions: ['catering.settings.manage'], tabLabel: 'Catering Settings', cateringTab: 'settings' } },
];

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
        path: 'profile',
        component: AccountProfileComponent,
        data: { tabLabel: 'Profile' },
      },
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
        canDeactivate: [unsavedChangesGuard],
        data: { permissions: ['appointment.book'], tabLabel: 'Create Appointment' },
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
        canDeactivate: [unsavedChangesGuard],
        data: { permissions: ['patient.create'], tabLabel: 'New Patient' },
      },
      {
        path: 'patients/id-card-settings',
        component: PatientIdCardSettingsComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['patient.id_card.configure'], tabLabel: 'Patient ID Card Settings' },
      },
      {
        path: 'patients/:patientId',
        component: PatientDetailComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['patient.view'], tabLabel: 'Patient Detail' },
      },
      {
        path: 'billing',
        component: BillingOverviewComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['billing.view'], tabLabel: 'Billing Overview' },
      },
      {
        path: 'billing/list',
        component: BillingDeskComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['billing.view'], tabLabel: 'Billing List', billingView: 'all' },
      },
      {
        path: 'billing/due-payments',
        component: BillingDeskComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['billing.view'], tabLabel: 'Due Payment List', billingView: 'due' },
      },
      {
        path: 'billing/create',
        component: BillingCreateComponent,
        canActivate: [permissionGuard],
        canDeactivate: [unsavedChangesGuard],
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
      ...bloodBankRoutes,
      ...cateringRoutes,
      {
        path: 'scanner/settings',
        component: ScannerSettingsComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['scanner.settings.manage'], tabLabel: 'Scanner Settings' },
      },
      {
        path: 'ai/settings',
        component: AiSettingsComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['ai.assistant.configure'], tabLabel: 'AI Assistant Settings' },
      },
      {
        path: 'notifications',
        component: NotificationCenterPageComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['notification.view'], tabLabel: 'Notification Center' },
      },
      {
        path: 'notifications/settings',
        component: NotificationSettingsComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['notification.configure'], tabLabel: 'Notification Settings' },
      },
      {
        path: 'queue',
        component: QueueWorkspaceComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['queue.view'], tabLabel: 'Queue Center' },
      },
      {
        path: 'manual',
        component: ShortcutSettingsComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['dashboard.view'], tabLabel: 'User Manual' },
      },
      { path: 'keyboard/shortcuts', redirectTo: 'manual', pathMatch: 'full' },
      {
        path: 'opd',
        component: OPDOverviewComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['opd.view'], tabLabel: 'OPD Dashboard' },
      },
      {
        path: 'opd/visits',
        component: OPDVisitListComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['opd.view'], tabLabel: 'OPD Visit List' },
      },
      {
        path: 'opd/register',
        component: OPDRegisterComponent,
        canActivate: [permissionGuard],
        canDeactivate: [unsavedChangesGuard],
        data: { permissions: ['opd.visit.create'], tabLabel: 'Register OPD Visit' },
      },
      {
        path: 'opd/settings',
        component: OPDSettingsComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['opd.settings.manage'], tabLabel: 'OPD Settings' },
      },
      {
        path: 'opd/configuration',
        component: ConfigurationWorkspaceComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['opd.settings.manage'], tabLabel: 'OPD Configuration', configurationContext: 'opd' },
      },
      {
        path: 'ipd',
        component: IPDOverviewComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['ipd.view'], tabLabel: 'IPD Overview' },
      },
      {
        path: 'ipd/admissions',
        component: IPDAdmissionListComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['ipd.view'], tabLabel: 'IPD Admission List' },
      },
      {
        path: 'ipd/admit',
        component: IPDAdmitComponent,
        canActivate: [permissionGuard],
        canDeactivate: [unsavedChangesGuard],
        data: { permissions: ['ipd.admit'], tabLabel: 'New Admission' },
      },
      {
        path: 'ipd/settings',
        component: IPDSettingsComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['ipd.settings.manage'], tabLabel: 'IPD Settings' },
      },
      {
        path: 'er',
        component: EROverviewComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['er.view'], tabLabel: 'ER' },
      },
      {
        path: 'er/register',
        component: ERRegisterComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['er.visit.manage'], tabLabel: 'Register ER Arrival' },
      },
      ...[
        ['inventory', 'Inventory', 'dashboard'],
        ['inventory/items', 'Inventory Items', 'items'],
        ['inventory/reagents', 'Inventory Reagents', 'reagents'],
        ['inventory/requests', 'Purchase Requests', 'requests'],
        ['inventory/reports', 'Inventory Reports', 'reports'],
      ].map(([path, tabLabel, inventoryTab]) => ({
        path,
        component: InventoryManagementComponent,
        canActivate: [permissionGuard],
        data: { permissions: [inventoryTab === 'requests' ? 'inventory.purchase' : inventoryTab === 'reports' ? 'inventory.reports.view' : 'inventory.view'], tabLabel, inventoryTab },
      })),
      ...[
        ['ot', 'OT Dashboard', 'dashboard', 'ot.view'],
        ['ot/bookings', 'OT Bookings', 'bookings', 'ot.view'],
        ['ot/calendar', 'OT Calendar', 'calendar', 'ot.view'],
        ['ot/rooms', 'OT Rooms', 'rooms', 'ot.room.manage'],
        ['ot/checklist', 'Pre-Op Checklist', 'checklist', 'ot.preop.manage'],
        ['ot/anesthesia', 'Anesthesia', 'anesthesia', 'ot.anesthesia.manage'],
        ['ot/case-sheet', 'OT Case Sheet', 'notes', 'ot.view'],
        ['ot/recovery', 'Post-Op Recovery', 'recovery', 'ot.recovery.manage'],
        ['ot/consumables', 'OT Consumables', 'consumables', 'ot.inventory.manage'],
        ['ot/billing', 'OT Billing', 'billing', 'ot.billing.manage'],
        ['ot/documents', 'OT Documents', 'documents', 'ot.documents.manage'],
        ['ot/reports', 'OT Reports', 'reports', 'ot.reports.view'],
      ].map(([path, tabLabel, otTab, permission]) => ({
        path,
        component: OTManagementComponent,
        canActivate: [permissionGuard],
        data: { permissions: [permission], tabLabel, otTab },
      })),
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
        path: 'laboratory/lis-simulator',
        component: LISSimulatorComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['laboratory.view'], tabLabel: 'LIS Simulator' },
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
      { path: 'reporting', redirectTo: 'reporting/library', pathMatch: 'full' },
      ...[
        ['reporting/library', 'Report Library', 'library', 'reporting.view'],
        ['reporting/finance', 'Financial Summary', 'finance', 'reporting.financial.view'],
        ['reporting/clinical', 'Clinical Operations', 'clinical', 'reporting.view'],
        ['reporting/doctor-referrals', 'Doctor Referral Summary', 'referrals', 'reporting.financial.view'],
      ].map(([path, tabLabel, reportingPage, permission]) => ({
        path,
        component: ReportingOverviewComponent,
        canActivate: [permissionGuard],
        data: { permissions: [permission], tabLabel, reportingPage },
      })),
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
        data: { permissions: ['pharmacy.settings.manage'], tabLabel: 'Pharmacy Settings' },
      },
      {
        path: 'pharmacy/medicine-types',
        component: PharmacyMasterPageComponent,
        canActivate: [permissionGuard],
        data: {
          permissions: ['pharmacy.settings.manage'],
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
          permissions: ['pharmacy.settings.manage'],
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
          permissions: ['pharmacy.settings.manage'],
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
          permissions: ['pharmacy.sale.create'],
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
        data: { permissions: ['pharmacy.purchase.manage'], tabLabel: 'Purchase History' },
      },
      {
        path: 'pharmacy/sales',
        component: PharmacySalesEditorComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['pharmacy.sale.create'], tabLabel: 'Medicine Sales' },
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
        data: { permissions: ['pharmacy.return'], tabLabel: 'Medicine Return List' },
      },
      {
        path: 'diagnostics/settings',
        component: PharmacyInvestigationSettingsComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['diagnostics.settings.manage'], tabLabel: 'Diagnostics Settings' },
      },
      {
        path: 'diagnostics/orders',
        component: PharmacyInvestigationsComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['diagnostics.order.manage'], tabLabel: 'Diagnostics Orders' },
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
        path: 'hr',
        component: HRPayrollComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['hr.view'], tabLabel: 'HR & Payroll', hrTab: 'dashboard' },
      },
      {
        path: 'hr/employees',
        component: HRPayrollComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['hr.view'], tabLabel: 'Employees', hrTab: 'employees' },
      },
      {
        path: 'hr/attendance',
        component: HRPayrollComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['hr.attendance.manage'], tabLabel: 'Attendance', hrTab: 'attendance' },
      },
      {
        path: 'hr/roster',
        component: HRPayrollComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['hr.shift.manage'], tabLabel: 'Duty Roster', hrTab: 'roster' },
      },
      {
        path: 'hr/leave',
        component: HRPayrollComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['hr.leave.manage'], tabLabel: 'Leave', hrTab: 'leave' },
      },
      {
        path: 'hr/documents',
        component: HRPayrollComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['hr.view'], tabLabel: 'Documents', hrTab: 'documents' },
      },
      {
        path: 'hr/payroll',
        component: HRPayrollComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['payroll.view'], tabLabel: 'Payroll', hrTab: 'payroll' },
      },
      {
        path: 'hr/recruitment',
        component: HRPayrollComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['hr.recruitment.manage'], tabLabel: 'Recruitment', hrTab: 'recruitment' },
      },
      {
        path: 'hr/performance',
        component: HRPayrollComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['hr.performance.manage'], tabLabel: 'Performance', hrTab: 'performance' },
      },
      {
        path: 'hr/reports',
        component: HRPayrollComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['hr.reports.view'], tabLabel: 'HR Reports', hrTab: 'reports' },
      },
      {
        path: 'hr/settings',
        component: HRPayrollComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['hr.settings.manage'], tabLabel: 'HR Settings', hrTab: 'settings' },
      },
      ...[
        ['accounting', 'Accounting', 'dashboard', 'accounting.view'],
        ['accounting/accounts', 'Chart of Accounts', 'accounts', 'accounting.view'],
        ['accounting/ledger', 'General Ledger', 'ledger', 'accounting.view'],
        ['accounting/vouchers', 'Vouchers', 'vouchers', 'accounting.journal.post'],
        ['accounting/collections', 'Payment Collection', 'collections', 'accounting.view'],
        ['accounting/receivables', 'Receivables', 'receivables', 'accounting.view'],
        ['accounting/payables', 'Payables', 'payables', 'accounting.view'],
        ['accounting/expenses', 'Expenses', 'expenses', 'accounting.view'],
        ['accounting/payroll', 'Payroll Accounting', 'payroll', 'accounting.view'],
        ['accounting/doctor-commission', 'Doctor Commission', 'doctor', 'accounting.view'],
        ['accounting/cash-closing', 'Cash Closing', 'cash', 'accounting.view'],
        ['accounting/bank', 'Bank Reconciliation', 'bank', 'accounting.view'],
        ['accounting/journals', 'Journal Entries', 'vouchers', 'accounting.journal.post'],
        ['accounting/reports', 'Finance Reports', 'reports', 'reporting.financial.view'],
        ['accounting/audit', 'Finance Audit', 'audit', 'audit.view'],
        ['accounting/journal', 'Journal Entries', 'vouchers', 'accounting.journal.post'],
      ].map(([path, tabLabel, accountingTab, permission]) => ({
        path,
        component: AccountingJournalComponent,
        canActivate: [permissionGuard],
        data: { permissions: [permission], tabLabel, accountingTab },
      })),
      {
        path: 'configuration',
        component: ConfigurationWorkspaceComponent,
        canActivate: [permissionGuard],
        data: { permissions: ['settings.configuration.manage'], tabLabel: 'Configuration Center', configurationContext: 'admin' },
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
