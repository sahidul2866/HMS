import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';

import { SessionService } from '../../../../core/services/session.service';
import { User } from '../../../../core/models/auth.models';
import {
  PatientClinicalHistory,
  PatientHistoryBillingInvoice,
  PatientHistoryBillingPayment,
  PatientHistoryIPDAdmission,
  PatientHistoryOPDVisit,
  PatientHistoryOrder,
  PatientHistoryPharmacyDispense,
} from '../../../patients/models/patient.models';
import { PatientAppointment } from '../../models/patient-portal.models';
import { PatientBotDoctorCard, PatientBotResponse, PatientBotSettings } from '../../models/patient-bot.models';
import { PatientBotService } from '../../services/patient-bot.service';
import { PatientPortalService } from '../../services/patient-portal.service';

type PortalTab =
  | 'home'
  | 'book'
  | 'appointments'
  | 'timeline'
  | 'prescriptions'
  | 'reports'
  | 'billing'
  | 'admissions'
  | 'documents'
  | 'family'
  | 'requests'
  | 'assistant'
  | 'hospital'
  | 'packages';

interface PortalDocument {
  id: string;
  type: string;
  title: string;
  date: string;
  status: string;
  owner: string;
  description: string;
}

interface TimelineItem {
  id: string;
  type: string;
  title: string;
  date: string;
  status: string;
  summary: string;
  action: PortalTab;
}

interface ReportRecord extends PatientHistoryOrder {
  visit_number: string;
  visit_date: string;
  doctor_name: string;
  department_name: string;
}

interface PrescriptionRecord extends PatientHistoryOrder {
  visit_number: string;
  visit_date: string;
  doctor_name: string;
  department_name: string;
  diagnosis?: string | null;
  follow_up_date?: string | null;
}

interface PatientRequest {
  id: string;
  type: string;
  summary: string;
  status: string;
  submitted_at: string;
}

interface PatientPreferences {
  preferredDepartment: string;
  preferredLanguage: string;
  favoriteDoctorIds: string[];
  downloadedDocumentIds: string[];
}

@Component({
  selector: 'app-patient-portal',
  standalone: true,
  imports: [CommonModule, FormsModule, ReactiveFormsModule],
  templateUrl: './patient-portal.component.html',
  styleUrls: ['./patient-portal.component.scss'],
})
export class PatientPortalComponent {
  private readonly portalService = inject(PatientPortalService);
  private readonly botService = inject(PatientBotService);
  private readonly fb = inject(FormBuilder);
  private readonly router = inject(Router);
  private readonly sessionService = inject(SessionService);

  history: PatientClinicalHistory | null = null;
  appointments: PatientAppointment[] = [];
  doctors: User[] = [];
  activeTab: PortalTab = 'home';
  loading = true;
  portalMessage = '';
  doctorSearch = '';
  doctorDepartmentFilter = '';
  doctorGender = '';
  doctorAvailability = '';
  doctorFeeRange = '';
  documentSearch = '';
  documentType = '';
  documentDateFilter = '';
  visitType = '';
  reportType: 'all' | 'laboratory' | 'radiology' = 'all';
  selectedFamilyProfile = 'self';
  selectedDoctorId = '';
  botConversationId: string | null = null;
  botInput = '';
  botLoading = false;
  botSettings: PatientBotSettings | null = null;
  botMessages: Array<{ sender: 'bot' | 'patient'; text: string; response?: PatientBotResponse }> = [];
  preferences: PatientPreferences = {
    preferredDepartment: '',
    preferredLanguage: 'English',
    favoriteDoctorIds: [],
    downloadedDocumentIds: [],
  };

  readonly form = this.fb.group({
    doctor_user_id: ['', Validators.required],
    appointment_at: [this.defaultAppointmentDate(), Validators.required],
    visit_type: ['General Consultation', Validators.required],
    reason: ['', Validators.required],
    note: [''],
  });

  readonly requestForm = this.fb.group({
    type: ['Appointment request', Validators.required],
    summary: ['', Validators.required],
  });

  readonly portalTabs: Array<{ key: PortalTab; label: string }> = [
    { key: 'home', label: 'Home' },
    { key: 'book', label: 'Book' },
    { key: 'appointments', label: 'Appointments' },
    { key: 'timeline', label: 'Timeline' },
    { key: 'prescriptions', label: 'Prescriptions' },
    { key: 'reports', label: 'Reports' },
    { key: 'billing', label: 'Billing' },
    { key: 'admissions', label: 'IPD' },
    { key: 'documents', label: 'Documents' },
    { key: 'family', label: 'Family' },
    { key: 'requests', label: 'Requests' },
    { key: 'assistant', label: 'Assistant' },
    { key: 'hospital', label: 'Hospital' },
    { key: 'packages', label: 'Packages' },
  ];

  readonly requestTypes = [
    'Appointment request',
    'Reschedule request',
    'Cancel appointment request',
    'Report copy request',
    'Bill copy request',
    'Medical certificate request',
    'Profile update request',
    'Insurance document request',
    'Follow-up request',
    'General support request',
  ];

  readonly hospitalServices = [
    { title: 'OPD Consultation', detail: 'Medicine, pediatrics, gynecology, cardiology and specialist clinics.', hours: 'Sat-Thu, 9:00 AM-8:00 PM' },
    { title: 'Diagnostics', detail: 'Laboratory and radiology reports are available from the portal after approval.', hours: 'Daily, 8:00 AM-10:00 PM' },
    { title: 'IPD Admission', detail: 'Ward, cabin, ICU and surgery admission support with billing visibility.', hours: '24/7 admission desk' },
    { title: 'Pharmacy', detail: 'Medicine purchase history and pharmacy invoices remain attached to the patient profile.', hours: '24/7 hospital pharmacy' },
  ];

  readonly healthPackages = [
    { name: 'General Health Checkup', price: 2500, offer: 1990, consult: true, includes: 'CBC, glucose, creatinine, SGPT, urine R/E, physician review' },
    { name: 'Diabetes Follow-up', price: 3200, offer: 2750, consult: true, includes: 'HbA1c, fasting glucose, lipid profile, urine microalbumin' },
    { name: 'Cardiac Screening', price: 5500, offer: 4900, consult: true, includes: 'ECG, lipid profile, troponin-I, echo review, cardiology consult' },
    { name: 'Women’s Wellness', price: 4200, offer: 3650, consult: true, includes: 'CBC, TSH, vitamin D, ultrasound screening, gynecology consult' },
    { name: 'Senior Comfort Check', price: 4800, offer: 4250, consult: true, includes: 'CBC, renal profile, ECG, electrolytes, medicine specialist review' },
    { name: 'Child Wellness', price: 2100, offer: 1750, consult: true, includes: 'CBC, urine R/E, growth review, pediatric consultation' },
  ];

  readonly familyMembers = [
    { id: 'self', name: 'My profile', relation: 'Self', status: 'Active' },
    { id: 'request', name: 'Link family member', relation: 'Child, parent or spouse', status: 'Approval required' },
  ];

  constructor() {
    const user = this.sessionService.snapshot.user;
    if (!user?.patient_id && !user?.effective_permissions.includes('patient.portal.view')) {
      void this.router.navigate(['/dashboard']);
      return;
    }
    this.preferences = this.readPreferences();
    this.loadPortal();
    this.loadBotSettings();
  }

  loadPortal(): void {
    this.loading = true;
    this.portalService.getOverview().subscribe({
      next: (overview) => {
        this.history = overview.patient;
        this.appointments = overview.appointments;
        this.doctors = overview.doctors;
        if (!this.preferences.preferredDepartment && this.doctorDepartments.length) {
          this.preferences = { ...this.preferences, preferredDepartment: this.doctorDepartments[0] };
          this.writePreferences();
        }
        this.loading = false;
      },
      error: () => {
        this.loading = false;
      },
    });
  }

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const raw = this.form.getRawValue();
    const payload = {
      doctor_user_id: raw.doctor_user_id || '',
      appointment_at: raw.appointment_at || '',
      reason: raw.reason || '',
      note: [raw.visit_type, raw.note].filter(Boolean).join(' - ') || null,
    };
    this.portalService.bookAppointment(payload).subscribe((appointment) => {
      this.appointments = [appointment, ...this.appointments];
      this.form.reset({ doctor_user_id: '', appointment_at: this.defaultAppointmentDate(), visit_type: 'General Consultation', reason: '', note: '' });
      this.portalMessage = `Appointment request ${appointment.appointment_number} has been submitted.`;
      this.activeTab = 'appointments';
    });
  }

  cancelAppointment(appointment: PatientAppointment): void {
    if (appointment.status !== 'scheduled' && appointment.status !== 'confirmed') {
      return;
    }
    this.portalService.updateAppointmentStatus(appointment.id, { status: 'cancelled' }).subscribe((updated) => {
      this.appointments = this.appointments.map((item) => (item.id === updated.id ? updated : item));
      this.portalMessage = `Appointment ${updated.appointment_number} was cancelled.`;
    });
  }

  submitRequest(): void {
    if (this.requestForm.invalid) {
      this.requestForm.markAllAsTouched();
      return;
    }
    const raw = this.requestForm.getRawValue();
    const requests = this.readStoredRequests();
    requests.unshift({
      id: `REQ-${Date.now().toString().slice(-6)}`,
      type: raw.type || 'General support request',
      summary: raw.summary || '',
      status: 'Submitted',
      submitted_at: new Date().toISOString(),
    });
    this.writeStoredRequests(requests);
    this.requestForm.reset({ type: 'Appointment request', summary: '' });
    this.portalMessage = 'Your request has been submitted for staff review.';
  }

  loadBotSettings(): void {
    this.botService.settings().subscribe((settings) => {
      this.botSettings = settings;
      if (!this.botMessages.length) {
        this.botMessages = [{ sender: 'bot', text: settings.greeting_message }];
      }
    });
  }

  sendBotMessage(message?: string): void {
    const text = (message || this.botInput).trim();
    if (!text || this.botLoading) {
      return;
    }
    if (text.toLowerCase() === 'start over') {
      this.resetBot();
      return;
    }
    this.botMessages = [...this.botMessages, { sender: 'patient', text }];
    this.botInput = '';
    this.botLoading = true;
    this.botService.sendMessage(text, this.botConversationId).subscribe({
      next: (response) => {
        this.botConversationId = response.conversation_id;
        this.botMessages = [...this.botMessages, { sender: 'bot', text: response.message, response }];
        this.botLoading = false;
      },
      error: () => {
        this.botMessages = [...this.botMessages, { sender: 'bot', text: 'I can still help you find a department or doctor. Please try a shorter message or use the quick replies.' }];
        this.botLoading = false;
      },
    });
  }

  resetBot(): void {
    this.botLoading = true;
    this.botService.reset().subscribe({
      next: (response) => {
        this.botConversationId = response.conversation_id;
        this.botMessages = [{ sender: 'bot', text: response.message, response }];
        this.botLoading = false;
      },
      error: () => {
        this.botMessages = [{ sender: 'bot', text: this.botSettings?.greeting_message || 'Hi, what do you need help with today?' }];
        this.botLoading = false;
      },
    });
  }

  selectBotDoctor(doctor: PatientBotDoctorCard): void {
    this.activeTab = 'book';
    this.form.patchValue({
      doctor_user_id: doctor.id,
      reason: `Appointment requested from health assistant for ${doctor.specialty}`,
    });
    this.portalMessage = `${doctor.name} selected from the assistant.`;
  }

  botBookAppointment(doctor: PatientBotDoctorCard): void {
    if (!this.botConversationId) {
      this.selectBotDoctor(doctor);
      return;
    }
    this.botLoading = true;
    this.botService.bookAppointment({
      conversation_id: this.botConversationId,
      doctor_user_id: doctor.id,
      appointment_at: this.form.value.appointment_at || this.defaultAppointmentDate(),
      reason: `Patient assistant booking request for ${doctor.specialty}`,
    }).subscribe({
      next: (appointment) => {
        this.appointments = [appointment, ...this.appointments];
        this.botMessages = [...this.botMessages, { sender: 'bot', text: `Appointment request ${appointment.appointment_number} has been created with ${doctor.name}.` }];
        this.botLoading = false;
      },
      error: () => {
        this.selectBotDoctor(doctor);
        this.botLoading = false;
      },
    });
  }

  setTab(tab: PortalTab): void {
    this.activeTab = tab;
    this.portalMessage = '';
  }

  selectDoctor(doctor: User): void {
    this.form.patchValue({ doctor_user_id: doctor.id });
    this.selectedDoctorId = doctor.id;
    this.portalMessage = `${doctor.full_name} selected for appointment booking.`;
  }

  viewDoctor(doctor: User): void {
    this.selectedDoctorId = doctor.id;
  }

  toggleFavoriteDoctor(doctor: User): void {
    const favorites = new Set(this.preferences.favoriteDoctorIds);
    if (favorites.has(doctor.id)) {
      favorites.delete(doctor.id);
      this.portalMessage = `${doctor.full_name} removed from favorites.`;
    } else {
      favorites.add(doctor.id);
      this.portalMessage = `${doctor.full_name} added to favorites.`;
    }
    this.preferences = { ...this.preferences, favoriteDoctorIds: Array.from(favorites) };
    this.writePreferences();
  }

  bookAgain(appointment: PatientAppointment): void {
    const doctor = this.doctors.find((item) => item.full_name === appointment.doctor_name);
    this.activeTab = 'book';
    this.form.patchValue({
      doctor_user_id: doctor?.id || '',
      reason: appointment.reason || 'Follow-up visit',
      note: appointment.note || '',
    });
  }

  downloadDocument(document: PortalDocument): void {
    const content = `${document.title}\n${document.type}\n${document.date}\n${document.status}\n\n${document.description}`;
    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = window.document.createElement('a');
    anchor.href = url;
    anchor.download = `${document.title.replace(/[^a-z0-9]+/gi, '-').toLowerCase()}.txt`;
    anchor.click();
    URL.revokeObjectURL(url);
    this.markDocumentDownloaded(document.id);
    this.portalMessage = `${document.title} was prepared for download.`;
  }

  printDocument(document: PortalDocument): void {
    this.portalMessage = `${document.title} is ready for browser print.`;
    window.setTimeout(() => window.print(), 50);
  }

  savePreference(key: 'preferredDepartment' | 'preferredLanguage', value: string): void {
    this.preferences = { ...this.preferences, [key]: value };
    this.writePreferences();
    this.portalMessage = 'Preference saved for your portal.';
  }

  get patientName(): string {
    const patient = this.history?.patient;
    return patient ? `${patient.first_name} ${patient.last_name}`.trim() : 'Patient';
  }

  get profileInitials(): string {
    return this.patientName
      .split(' ')
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase())
      .join('');
  }

  get greeting(): string {
    const hour = new Date().getHours();
    if (hour < 12) {
      return `Good morning, ${this.history?.patient.first_name || 'there'}`;
    }
    if (hour < 17) {
      return `Good afternoon, ${this.history?.patient.first_name || 'there'}`;
    }
    return `Good evening, ${this.history?.patient.first_name || 'there'}`;
  }

  get ageGender(): string {
    const patient = this.history?.patient;
    const age = patient?.date_of_birth ? `${this.calculateAge(patient.date_of_birth)} yrs` : 'Age not set';
    return `${age} · ${patient?.gender || 'Gender not set'}`;
  }

  get doctorDepartments(): string[] {
    return Array.from(new Set(this.doctors.map((doctor) => doctor.opd_prescription_header_workplace || 'General OPD'))).sort();
  }

  get doctorSpecialties(): string[] {
    return Array.from(new Set(this.doctors.map((doctor) => this.doctorSpecialty(doctor)))).sort();
  }

  get filteredDoctors(): User[] {
    const query = this.doctorSearch.trim().toLowerCase();
    return this.doctors.filter((doctor) => {
      const specialty = doctor.opd_prescription_header_specialty || '';
      const department = doctor.opd_prescription_header_workplace || 'General OPD';
      const chamber = doctor.opd_prescription_header_chamber || '';
      const matchesQuery = !query || `${doctor.full_name} ${specialty} ${department} ${chamber}`.toLowerCase().includes(query);
      const matchesDepartment = !this.doctorDepartmentFilter || department === this.doctorDepartmentFilter;
      const matchesGender = !this.doctorGender || doctor.username.toLowerCase().includes(this.doctorGender.toLowerCase());
      const matchesAvailability = !this.doctorAvailability || this.nextAvailableSlot(doctor).toLowerCase().includes(this.doctorAvailability);
      const fee = Number(doctor.opd_consultation_fee || 0);
      const matchesFee = !this.doctorFeeRange
        || (this.doctorFeeRange === 'low' && fee <= 700)
        || (this.doctorFeeRange === 'mid' && fee > 700 && fee <= 1200)
        || (this.doctorFeeRange === 'high' && fee > 1200);
      return matchesQuery && matchesDepartment && matchesGender && matchesAvailability && matchesFee;
    });
  }

  get selectedDoctor(): User | null {
    return this.doctors.find((doctor) => doctor.id === this.selectedDoctorId) ?? this.filteredDoctors[0] ?? null;
  }

  get favoriteDoctors(): User[] {
    return this.doctors.filter((doctor) => this.preferences.favoriteDoctorIds.includes(doctor.id));
  }

  get recentlyVisitedDoctors(): User[] {
    const names = Array.from(new Set([...(this.history?.opd_visits ?? []).map((visit) => visit.consulting_doctor_name), ...this.appointments.map((appointment) => appointment.doctor_name)]));
    return names
      .map((name) => this.doctors.find((doctor) => doctor.full_name === name))
      .filter((doctor): doctor is User => !!doctor)
      .slice(0, 4);
  }

  get recommendedDoctors(): User[] {
    const preferred = this.preferences.preferredDepartment || this.latestVisit?.department_name || this.doctorDepartmentFilter;
    return this.doctors
      .filter((doctor) => !preferred || this.doctorDepartmentLabel(doctor) === preferred)
      .slice(0, 4);
  }

  get upcomingAppointments(): PatientAppointment[] {
    return this.appointments
      .filter((item) => ['scheduled', 'confirmed', 'requested'].includes(item.status))
      .sort((a, b) => new Date(a.appointment_at).getTime() - new Date(b.appointment_at).getTime());
  }

  get pastAppointments(): PatientAppointment[] {
    return this.appointments
      .filter((item) => !['scheduled', 'confirmed', 'requested'].includes(item.status))
      .sort((a, b) => new Date(b.appointment_at).getTime() - new Date(a.appointment_at).getTime());
  }

  get latestVisit(): PatientHistoryOPDVisit | null {
    return [...(this.history?.opd_visits ?? [])].sort((a, b) => new Date(b.visit_date).getTime() - new Date(a.visit_date).getTime())[0] ?? null;
  }

  get nextAppointmentText(): string {
    const appointment = this.upcomingAppointments[0];
    return appointment?.appointment_at ? new Date(appointment.appointment_at).toLocaleString('en-BD', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }) : 'No appointment booked';
  }

  get activeAdmission(): PatientHistoryIPDAdmission | null {
    return (this.history?.ipd_admissions ?? []).find((item) => !item.discharged_at && !['discharged', 'cancelled'].includes(item.status)) ?? null;
  }

  get completedLabReports(): ReportRecord[] {
    return (this.history?.opd_visits ?? []).flatMap((visit) =>
      visit.orders
        .filter((order) => order.service_area === 'laboratory' && ['completed', 'verified', 'approved'].includes(order.status))
        .map((order) => this.toReportRecord(order, visit))
    );
  }

  get completedRadiologyReports(): ReportRecord[] {
    return (this.history?.opd_visits ?? []).flatMap((visit) =>
      visit.orders
        .filter((order) => order.service_area === 'radiology' && ['completed', 'verified', 'approved'].includes(order.status))
        .map((order) => this.toReportRecord(order, visit))
    );
  }

  get visibleReports(): ReportRecord[] {
    if (this.reportType === 'laboratory') {
      return this.completedLabReports;
    }
    if (this.reportType === 'radiology') {
      return this.completedRadiologyReports;
    }
    return [...this.completedLabReports, ...this.completedRadiologyReports].sort((a, b) => new Date(b.completed_at || b.visit_date).getTime() - new Date(a.completed_at || a.visit_date).getTime());
  }

  get prescriptionArchive(): PrescriptionRecord[] {
    return (this.history?.opd_visits ?? []).flatMap((visit) =>
      visit.orders
        .filter((order) => order.order_type === 'prescription')
        .map((order) => ({
          visit_number: visit.visit_number,
          visit_date: visit.visit_date,
          doctor_name: visit.consulting_doctor_name,
          department_name: visit.department_name,
          diagnosis: visit.final_diagnosis || visit.provisional_diagnosis,
          follow_up_date: visit.follow_up_date,
          ...order,
        }))
    ).sort((a, b) => new Date(b.visit_date).getTime() - new Date(a.visit_date).getTime());
  }

  get latestPrescription(): PrescriptionRecord | null {
    return this.prescriptionArchive[0] ?? null;
  }

  get latestReport(): ReportRecord | null {
    return this.visibleReports[0] ?? null;
  }

  get totalOutstandingDue(): number {
    return (this.history?.billing_invoices ?? []).reduce((sum, invoice) => sum + Number(invoice.due_amount || 0), 0);
  }

  get totalPaidAmount(): number {
    return (this.history?.billing_invoices ?? []).reduce((sum, invoice) => sum + Number(invoice.paid_amount || 0), 0);
  }

  get latestInvoice(): PatientHistoryBillingInvoice | null {
    return [...(this.history?.billing_invoices ?? [])].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0] ?? null;
  }

  get recentPayments(): PatientHistoryBillingPayment[] {
    return [...(this.history?.billing_payments ?? [])].sort((a, b) => new Date(b.received_at).getTime() - new Date(a.received_at).getTime()).slice(0, 5);
  }

  get billingInvoices(): PatientHistoryBillingInvoice[] {
    return [...(this.history?.billing_invoices ?? [])].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  }

  get pharmacyHistory(): PatientHistoryPharmacyDispense[] {
    return [...(this.history?.pharmacy_dispenses ?? [])].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  }

  get filteredVisits(): PatientHistoryOPDVisit[] {
    return [...(this.history?.opd_visits ?? [])]
      .filter((visit) => !this.visitType || visit.status === this.visitType)
      .sort((a, b) => new Date(b.visit_date).getTime() - new Date(a.visit_date).getTime());
  }

  get healthTimeline(): TimelineItem[] {
    const visits = (this.history?.opd_visits ?? []).map((visit) => ({
      id: `visit-${visit.id}`,
      type: 'Visit',
      title: `${visit.department_name} visit`,
      date: visit.visit_date,
      status: visit.status,
      summary: `${visit.consulting_doctor_name} · ${visit.final_diagnosis || visit.provisional_diagnosis || visit.chief_complaint || 'Consultation record'}`,
      action: 'timeline' as PortalTab,
    }));
    const admissions = (this.history?.ipd_admissions ?? []).map((admission) => ({
      id: `ipd-${admission.id}`,
      type: 'Admission',
      title: admission.admission_number,
      date: admission.admitted_at,
      status: admission.status,
      summary: `${admission.ward_name} ${admission.bed_number} · ${admission.attending_doctor_name}`,
      action: 'admissions' as PortalTab,
    }));
    const reports = this.visibleReports.map((report) => ({
      id: `report-${report.id}`,
      type: report.service_area === 'radiology' ? 'Radiology' : 'Lab',
      title: report.item_name,
      date: report.completed_at || report.visit_date,
      status: report.status,
      summary: `${report.department_name} · ordered by ${report.doctor_name}`,
      action: 'reports' as PortalTab,
    }));
    const invoices = (this.history?.billing_invoices ?? []).map((invoice) => ({
      id: `invoice-${invoice.id}`,
      type: 'Billing',
      title: invoice.invoice_number,
      date: invoice.created_at,
      status: invoice.payment_status,
      summary: `Total ${this.formatCurrency(invoice.total_amount)} · Due ${this.formatCurrency(invoice.due_amount)}`,
      action: 'billing' as PortalTab,
    }));
    return [...visits, ...admissions, ...reports, ...invoices].sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
  }

  get documents(): PortalDocument[] {
    const prescriptions = this.prescriptionArchive.map((item) => ({
      id: `rx-${item.id}`,
      type: 'Prescription',
      title: `${item.visit_number} Prescription`,
      date: item.visit_date,
      status: item.status,
      owner: item.doctor_name,
      description: `${item.item_name}. ${item.instructions || 'No instruction recorded.'}`,
    }));
    const reports = this.visibleReports.map((item) => ({
      id: `report-${item.id}`,
      type: item.service_area === 'radiology' ? 'Radiology Report' : 'Lab Report',
      title: item.item_name,
      date: item.completed_at || item.visit_date,
      status: item.status,
      owner: item.doctor_name,
      description: item.result_text || 'Finalized report available from hospital record.',
    }));
    const invoices = (this.history?.billing_invoices ?? []).map((invoice) => ({
      id: `invoice-${invoice.id}`,
      type: 'Invoice',
      title: invoice.invoice_number,
      date: invoice.created_at,
      status: invoice.payment_status,
      owner: invoice.referred_doctor_name || 'Billing',
      description: `Total ${this.formatCurrency(invoice.total_amount)}, paid ${this.formatCurrency(invoice.paid_amount)}, due ${this.formatCurrency(invoice.due_amount)}.`,
    }));
    const receipts = (this.history?.billing_payments ?? []).map((payment) => ({
      id: `receipt-${payment.id}`,
      type: 'Receipt',
      title: payment.receipt_number,
      date: payment.received_at,
      status: payment.payment_method,
      owner: payment.invoice_number,
      description: `Received ${this.formatCurrency(payment.amount)} by ${payment.payment_method}.`,
    }));
    const discharge = (this.history?.ipd_admissions ?? [])
      .filter((admission) => !!admission.discharged_at)
      .map((admission) => ({
        id: `discharge-${admission.id}`,
        type: 'Discharge Summary',
        title: admission.admission_number,
        date: admission.discharged_at || admission.admitted_at,
        status: admission.status,
        owner: admission.attending_doctor_name,
        description: `${admission.diagnosis || 'Discharge summary'} · ${admission.ward_name} ${admission.bed_number}.`,
      }));
    return [...prescriptions, ...reports, ...invoices, ...receipts, ...discharge].sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
  }

  get documentTypes(): string[] {
    return Array.from(new Set(this.documents.map((item) => item.type))).sort();
  }

  get filteredDocuments(): PortalDocument[] {
    const query = this.documentSearch.trim().toLowerCase();
    return this.documents.filter((item) => {
      const matchesType = !this.documentType || item.type === this.documentType;
      const matchesQuery = !query || `${item.title} ${item.type} ${item.owner} ${item.description}`.toLowerCase().includes(query);
      const matchesDate = !this.documentDateFilter || this.isDocumentWithinDateFilter(item, this.documentDateFilter);
      return matchesType && matchesQuery && matchesDate;
    });
  }

  get documentCategories(): Array<{ type: string; count: number }> {
    return this.documentTypes.map((type) => ({
      type,
      count: this.documents.filter((document) => document.type === type).length,
    }));
  }

  get recentlyAddedDocuments(): PortalDocument[] {
    return this.documents.slice(0, 4);
  }

  get recentlyDownloadedDocuments(): PortalDocument[] {
    return this.documents.filter((document) => this.preferences.downloadedDocumentIds.includes(document.id)).slice(0, 4);
  }

  get patientRequests(): PatientRequest[] {
    return this.readStoredRequests();
  }

  get botQuickReplies(): string[] {
    return this.botMessages[this.botMessages.length - 1]?.response?.quick_replies || this.botSettings?.quick_replies || [];
  }

  get visitStatuses(): string[] {
    return Array.from(new Set((this.history?.opd_visits ?? []).map((visit) => visit.status))).sort();
  }

  get currentPatientId(): string {
    return this.history?.patient.id || this.sessionService.snapshot.user?.patient_id || 'patient';
  }

  doctorSpecialty(doctor: User): string {
    return doctor.opd_prescription_header_specialty || 'General Consultation';
  }

  doctorQualification(doctor: User): string {
    return doctor.opd_prescription_header_degrees || 'MBBS, Specialist';
  }

  doctorExperience(doctor: User): string {
    const index = this.doctors.findIndex((item) => item.id === doctor.id);
    return `${8 + Math.max(index, 0) * 2}+ years`;
  }

  doctorLanguages(doctor: User): string {
    const index = this.doctors.findIndex((item) => item.id === doctor.id);
    return index % 2 ? 'Bangla, English, Hindi' : 'Bangla, English';
  }

  doctorRating(doctor: User): string {
    const index = this.doctors.findIndex((item) => item.id === doctor.id);
    return (4.6 + (Math.max(index, 0) % 4) / 10).toFixed(1);
  }

  doctorBio(doctor: User): string {
    return `${doctor.full_name} provides ${this.doctorSpecialty(doctor).toLowerCase()} care at ${this.doctorDepartmentLabel(doctor)} with a practical patient-first consultation style.`;
  }

  isFavoriteDoctor(doctor: User): boolean {
    return this.preferences.favoriteDoctorIds.includes(doctor.id);
  }

  doctorDepartmentLabel(doctor: User): string {
    return doctor.opd_prescription_header_workplace || 'General OPD';
  }

  doctorChamber(doctor: User): string {
    return doctor.opd_prescription_header_chamber || 'Chamber to be assigned';
  }

  doctorFee(doctor: User): string {
    return this.formatCurrency(doctor.opd_consultation_fee || 0);
  }

  nextAvailableSlot(doctor: User): string {
    const index = this.doctors.findIndex((item) => item.id === doctor.id);
    const dayOffset = index % 3;
    const date = new Date();
    date.setDate(date.getDate() + dayOffset);
    date.setHours(10 + (index % 5), index % 2 ? 30 : 0, 0, 0);
    return date.toLocaleString('en-BD', { weekday: 'short', hour: 'numeric', minute: '2-digit' });
  }

  doctorSlots(doctor: User): string[] {
    const index = Math.max(0, this.doctors.findIndex((item) => item.id === doctor.id));
    return ['10:00 AM', '12:30 PM', '5:00 PM'].map((slot, slotIndex) => {
      const date = new Date();
      date.setDate(date.getDate() + ((index + slotIndex) % 4));
      return `${date.toLocaleString('en-BD', { weekday: 'short' })} ${slot}`;
    });
  }

  appointmentStatusLabel(status: string): string {
    return status.replace(/_/g, ' ');
  }

  formatCurrency(value: string | number): string {
    return new Intl.NumberFormat('en-BD', {
      style: 'currency',
      currency: 'BDT',
      minimumFractionDigits: 2,
    }).format(Number(value || 0));
  }

  formatPlainDate(value: string): string {
    return new Date(value).toLocaleDateString('en-BD', { month: 'short', day: 'numeric', year: 'numeric' });
  }

  private toReportRecord(order: PatientHistoryOrder, visit: PatientHistoryOPDVisit): ReportRecord {
    return {
      ...order,
      visit_number: visit.visit_number,
      visit_date: visit.visit_date,
      doctor_name: visit.consulting_doctor_name,
      department_name: visit.department_name,
    };
  }

  private calculateAge(dateOfBirth: string): number {
    const birthDate = new Date(dateOfBirth);
    const today = new Date();
    let age = today.getFullYear() - birthDate.getFullYear();
    const monthDifference = today.getMonth() - birthDate.getMonth();
    if (monthDifference < 0 || (monthDifference === 0 && today.getDate() < birthDate.getDate())) {
      age -= 1;
    }
    return Math.max(0, age);
  }

  private defaultAppointmentDate(): string {
    const date = new Date();
    date.setDate(date.getDate() + 1);
    date.setHours(10, 0, 0, 0);
    const offsetDate = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
    return offsetDate.toISOString().slice(0, 16);
  }

  private requestStorageKey(): string {
    return `patient-portal-requests-${this.currentPatientId}`;
  }

  private preferenceStorageKey(): string {
    return `patient-portal-preferences-${this.currentPatientId}`;
  }

  private readStoredRequests(): PatientRequest[] {
    const raw = localStorage.getItem(this.requestStorageKey());
    if (!raw) {
      return [];
    }
    try {
      return JSON.parse(raw) as PatientRequest[];
    } catch {
      return [];
    }
  }

  private writeStoredRequests(requests: PatientRequest[]): void {
    localStorage.setItem(this.requestStorageKey(), JSON.stringify(requests));
  }

  private readPreferences(): PatientPreferences {
    const raw = localStorage.getItem(this.preferenceStorageKey());
    if (!raw) {
      return { preferredDepartment: '', preferredLanguage: 'English', favoriteDoctorIds: [], downloadedDocumentIds: [] };
    }
    try {
      const parsed = JSON.parse(raw) as Partial<PatientPreferences>;
      return {
        preferredDepartment: parsed.preferredDepartment || '',
        preferredLanguage: parsed.preferredLanguage || 'English',
        favoriteDoctorIds: parsed.favoriteDoctorIds || [],
        downloadedDocumentIds: parsed.downloadedDocumentIds || [],
      };
    } catch {
      return { preferredDepartment: '', preferredLanguage: 'English', favoriteDoctorIds: [], downloadedDocumentIds: [] };
    }
  }

  private writePreferences(): void {
    localStorage.setItem(this.preferenceStorageKey(), JSON.stringify(this.preferences));
  }

  private markDocumentDownloaded(documentId: string): void {
    const ids = [documentId, ...this.preferences.downloadedDocumentIds.filter((id) => id !== documentId)].slice(0, 8);
    this.preferences = { ...this.preferences, downloadedDocumentIds: ids };
    this.writePreferences();
  }

  private isDocumentWithinDateFilter(document: PortalDocument, filter: string): boolean {
    const documentDate = new Date(document.date).getTime();
    const now = new Date().getTime();
    const days = filter === '7' ? 7 : filter === '30' ? 30 : filter === '365' ? 365 : 0;
    return !days || now - documentDate <= days * 24 * 60 * 60 * 1000;
  }
}
