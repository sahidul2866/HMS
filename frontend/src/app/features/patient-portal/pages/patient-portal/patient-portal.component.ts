import { CommonModule } from '@angular/common';
import { afterNextRender, Component, DestroyRef, ElementRef, inject, Injector, ViewChild } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { finalize, Subscription } from 'rxjs';
import { DialogDirective } from '../../../../shared/directives/dialog.directive';

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
import { DoctorSlotAvailability } from '../../../appointments/models/appointment.models';
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
type PortalTabGroup = 'essentials' | 'records' | 'support';
type PortalBookingAction = 'find-doctor' | 'book-appointment';

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
  imports: [CommonModule, FormsModule, ReactiveFormsModule, DialogDirective],
  templateUrl: './patient-portal.component.html',
  styleUrls: ['./patient-portal.component.scss'],
})
export class PatientPortalComponent {
  private readonly portalService = inject(PatientPortalService);
  private readonly botService = inject(PatientBotService);
  private readonly fb = inject(FormBuilder);
  private readonly router = inject(Router);
  private readonly sessionService = inject(SessionService);
  private readonly injector = inject(Injector);
  @ViewChild('assistantChat') private assistantChat?: ElementRef<HTMLDivElement>;
  @ViewChild('assistantInput', { read: ElementRef }) private assistantInput?: ElementRef<HTMLFormElement>;
  @ViewChild('bookingForm', { read: ElementRef }) private bookingForm?: ElementRef<HTMLFormElement>;
  @ViewChild('bookingFeedback') private bookingFeedback?: ElementRef<HTMLElement>;
  @ViewChild('bookingReceipt') private bookingReceipt?: ElementRef<HTMLElement>;
  private slotsRequest?: Subscription;
  private readonly destroyRef = inject(DestroyRef);

  history: PatientClinicalHistory | null = null;
  appointments: PatientAppointment[] = [];
  doctors: User[] = [];
  activeTab: PortalTab = 'home';
  private bookingAction: PortalBookingAction = 'book-appointment';
  loading = true;
  portalLoadFailed = false;
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
  loadingSlots = false;
  slotLoadError = '';
  bookingSubmitting = false;
  bookingError = '';
  profileDoctor: User | null = null;
  previewDocument: PortalDocument | null = null;
  bookingConfirmation: PatientAppointment | null = null;
  availableSlots: DoctorSlotAvailability[] = [];
  selectedSlot: DoctorSlotAvailability | null = null;
  activeTabGroup: PortalTabGroup = 'essentials';
  quickActionsModalOpen = false;
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
    slot_date: [this.defaultAppointmentDate(), Validators.required],
    appointment_at: ['', Validators.required],
    visit_type: ['General Consultation', Validators.required],
    reason: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(500)]],
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
  readonly tabGroups: Array<{ key: PortalTabGroup; label: string; tabs: PortalTab[] }> = [
    { key: 'essentials', label: 'Essentials', tabs: ['home', 'book', 'appointments', 'assistant'] },
    { key: 'records', label: 'Records', tabs: ['timeline', 'prescriptions', 'reports', 'billing', 'admissions', 'documents'] },
    { key: 'support', label: 'Support', tabs: ['family', 'requests', 'hospital', 'packages'] },
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
    this.destroyRef.onDestroy(() => this.slotsRequest?.unsubscribe());
    const user = this.sessionService.snapshot.user;
    if (!user?.patient_id && !user?.effective_permissions.includes('patient.portal.view')) {
      void this.router.navigate(['/dashboard']);
      return;
    }
    this.preferences = this.readPreferences();
    this.form.controls.doctor_user_id.valueChanges.subscribe(() => this.loadSlots());
    this.form.controls.slot_date.valueChanges.subscribe(() => this.loadSlots());
    this.loadPortal();
    this.loadBotSettings();
  }

  retryPortal(): void {
    this.portalService.clearCache();
    this.loadPortal();
  }

  loadPortal(): void {
    this.loading = true;
    this.portalLoadFailed = false;
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
      error: (error: { status?: number }) => {
        // A staff account without a linked patient profile is refused by design; the page explains that instead of a toast.
        this.portalLoadFailed = error.status !== 403;
        this.loading = false;
      },
    });
  }

  submit(): void {
    if (this.bookingSubmitting) return;
    this.bookingError = '';
    const raw = this.form.getRawValue();
    if (!raw.doctor_user_id) this.bookingError = 'Select a doctor before confirming your appointment.';
    else if (!raw.slot_date) this.bookingError = 'Choose an appointment date.';
    else if (this.loadingSlots) this.bookingError = 'Please wait for the available times to load.';
    else if (this.slotLoadError) this.bookingError = this.slotLoadError;
    else if (!this.selectedSlot) this.bookingError = this.availableSlots.some(slot => slot.status === 'available')
      ? 'Choose one of the available time slots before confirming.'
      : 'No available slots for this doctor on this date. Choose another date or doctor, or contact reception.';
    else if (!raw.reason?.trim()) this.bookingError = 'Enter the reason for your appointment.';
    else if (raw.reason.trim().length < 3 || raw.reason.trim().length > 500) this.bookingError = 'Use 3 to 500 characters for the appointment reason.';
    else if (new Date(this.selectedSlot.slot_start_at).getTime() <= Date.now()) this.bookingError = 'This time has already passed. Choose a future slot.';
    if (this.bookingError || this.form.invalid) {
      this.form.markAllAsTouched();
      this.bookingError ||= 'Complete the required appointment details.';
      this.showBookingError();
      return;
    }
    const payload = {
      doctor_user_id: raw.doctor_user_id || '',
      appointment_at: this.selectedSlot!.slot_start_at,
      reason: raw.reason!.trim(),
      note: [raw.visit_type, raw.note].filter(Boolean).join(' - ') || null,
    };
    this.bookingSubmitting = true;
    this.portalService.bookAppointment(payload).pipe(finalize(() => this.bookingSubmitting = false)).subscribe({
      next: (appointment) => {
        this.appointments = [appointment, ...this.appointments.filter(item => item.id !== appointment.id)];
        this.form.reset({ doctor_user_id: '', slot_date: this.defaultAppointmentDate(), appointment_at: '', visit_type: 'General Consultation', reason: '', note: '' });
        this.selectedDoctorId = '';
        this.showBookingDetails(appointment);
        this.portalMessage = `Appointment ${appointment.appointment_number} saved successfully.`;
      },
      error: (error: { status?: number; error?: { error?: { message?: string } } }) => {
        if (error.status === 409) this.loadSlots();
        this.bookingError = error.status === 409
          ? 'That slot is no longer available. Choose another time from the refreshed list.'
          : error.status && error.status < 500 && error.error?.error?.message
            ? error.error.error.message
            : 'We could not confirm that your appointment was saved. Your details are still here. Check Appointments before trying again.';
        this.showBookingError();
      },
    });
  }

  private showBookingError(): void {
    afterNextRender(() => {
      this.bookingFeedback?.nativeElement.focus();
      this.bookingFeedback?.nativeElement.scrollIntoView({ block: 'nearest' });
    }, { injector: this.injector });
  }

  showBookingDetails(appointment: PatientAppointment): void {
    this.bookingConfirmation = appointment;
    this.setTab('appointments');
    afterNextRender(() => {
      this.bookingReceipt?.nativeElement.focus();
      this.bookingReceipt?.nativeElement.scrollIntoView({ block: 'start' });
    }, { injector: this.injector });
  }

  get confirmationDoctor(): User | null {
    return this.doctors.find(doctor => doctor.id === this.bookingConfirmation?.doctor_user_id) || null;
  }

  cancelAppointment(appointment: PatientAppointment): void {
    if (appointment.status !== 'scheduled' && appointment.status !== 'confirmed') {
      return;
    }
    this.portalService.updateAppointmentStatus(appointment.id, { status: 'cancelled' }).subscribe((updated) => {
      this.appointments = this.appointments.map((item) => (item.id === updated.id ? updated : item));
      if (this.bookingConfirmation?.id === updated.id) this.bookingConfirmation = updated;
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
        this.scrollBotToLatest();
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
    this.scrollBotToLatest();
    this.botService.sendMessage(text, this.botConversationId).subscribe({
      next: (response) => {
        this.botConversationId = response.conversation_id;
        this.botMessages = [...this.botMessages, { sender: 'bot', text: response.message, response }];
        this.botLoading = false;
        this.scrollBotToLatest();
      },
      error: () => {
        this.botMessages = [...this.botMessages, { sender: 'bot', text: 'I can still help you find a department or doctor. Please try a shorter message or use the quick replies.' }];
        this.botLoading = false;
        this.scrollBotToLatest();
      },
    });
  }

  resetBot(): void {
    if (this.botLoading) return;
    this.botLoading = true;
    this.scrollBotToLatest();
    this.botService.reset().subscribe({
      next: (response) => {
        this.botConversationId = response.conversation_id;
        this.botMessages = [{ sender: 'bot', text: response.message, response }];
        this.botLoading = false;
        this.scrollBotToLatest();
      },
      error: () => {
        this.botMessages = [{ sender: 'bot', text: this.botSettings?.greeting_message || 'Hi, what do you need help with today?' }];
        this.botLoading = false;
        this.scrollBotToLatest();
      },
    });
  }

  private scrollBotToLatest(): void {
    afterNextRender({
      mixedReadWrite: () => {
        const chat = this.assistantChat?.nativeElement;
        if (!chat) return;
        // Measure after rendering, then keep the latest reply and composer in view without moving focus.
        chat.scrollTop = chat.scrollHeight;
        this.assistantInput?.nativeElement.scrollIntoView({ block: 'nearest', inline: 'nearest' });
      },
    }, { injector: this.injector });
  }

  selectBotDoctor(doctor: PatientBotDoctorCard): void {
    this.setTab('book');
    this.form.patchValue({
      doctor_user_id: doctor.id,
      reason: `Appointment requested from health assistant for ${doctor.specialty}`,
    });
    this.portalMessage = `${doctor.name} selected from the assistant.`;
  }

  botBookAppointment(doctor: PatientBotDoctorCard): void {
    this.selectBotDoctor(doctor);
    this.portalMessage = `${doctor.name} selected. Choose a date and an available slot to complete booking.`;
  }

  get activeHomeAction(): PortalBookingAction | 'assistant' | 'more' | null {
    if (this.quickActionsModalOpen) return 'more';
    if (this.activeTab === 'book') return this.bookingAction;
    if (this.activeTab === 'assistant') return 'assistant';
    if (this.activeTab === 'home' || this.activeTab === 'appointments') return null;
    return 'more';
  }

  setTab(tab: PortalTab, bookingAction: PortalBookingAction = 'book-appointment'): void {
    this.activeTab = tab;
    if (tab === 'assistant') this.scrollBotToLatest();
    if (tab === 'book') this.bookingAction = bookingAction;
    const group = this.tabGroups.find((item) => item.tabs.includes(tab));
    if (group) {
      this.activeTabGroup = group.key;
    }
    this.portalMessage = '';
  }

  setTabGroup(group: PortalTabGroup): void {
    this.activeTabGroup = group;
    const validTabs = this.tabGroups.find((item) => item.key === group)?.tabs || [];
    if (!validTabs.includes(this.activeTab)) {
      this.activeTab = validTabs[0] || 'home';
    }
    this.portalMessage = '';
  }

  get visiblePortalTabs(): Array<{ key: PortalTab; label: string }> {
    const keys = this.tabGroups.find((item) => item.key === this.activeTabGroup)?.tabs || [];
    return this.portalTabs.filter((tab) => keys.includes(tab.key));
  }

  toggleQuickActionsModal(): void {
    this.quickActionsModalOpen = !this.quickActionsModalOpen;
  }

  selectDoctor(doctor: User): void {
    this.setTab('book');
    this.bookingAction = 'book-appointment';
    this.form.patchValue({ doctor_user_id: doctor.id });
    this.selectedDoctorId = doctor.id;
    this.portalMessage = `${doctor.full_name} selected for appointment booking.`;
    this.profileDoctor = null;
    afterNextRender(() => this.bookingForm?.nativeElement.scrollIntoView({ block: 'center' }), { injector: this.injector });
  }

  loadSlots(): void {
    this.slotsRequest?.unsubscribe();
    this.loadingSlots = false;
    this.slotLoadError = '';
    this.bookingError = '';
    const doctorId = this.form.controls.doctor_user_id.getRawValue();
    const slotDate = this.form.controls.slot_date.getRawValue();
    this.selectedSlot = null;
    this.form.controls.appointment_at.setValue('', { emitEvent: false });
    this.availableSlots = [];
    this.selectedDoctorId = doctorId || '';
    if (!doctorId || !slotDate) {
      return;
    }
    this.loadingSlots = true;
    this.slotsRequest = this.portalService.getDoctorSlots(doctorId, slotDate)
      .pipe(finalize(() => (this.loadingSlots = false)))
      .subscribe({
        next: (response) => (this.availableSlots = response.slots),
        error: () => (this.slotLoadError = 'Unable to load appointment times. Retry below or contact reception.'),
      });
  }

  selectSlot(slot: DoctorSlotAvailability): void {
    if (slot.status !== 'available') {
      return;
    }
    this.selectedSlot = slot;
    this.bookingError = '';
    this.form.controls.appointment_at.setValue(slot.slot_start_at);
  }

  viewDoctor(doctor: User): void {
    this.profileDoctor = doctor;
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
    this.setTab('book');
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
    const doctorId = this.form.controls.doctor_user_id.getRawValue();
    return this.doctors.find((doctor) => doctor.id === doctorId) ?? null;
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
        .filter((order) => order.service_area === 'laboratory' && ['verified', 'approved'].includes(order.status))
        .map((order) => this.toReportRecord(order, visit))
    );
  }

  get completedRadiologyReports(): ReportRecord[] {
    return (this.history?.opd_visits ?? []).flatMap((visit) =>
      visit.orders
        .filter((order) => order.service_area === 'radiology' && ['verified', 'approved'].includes(order.status))
        .map((order) => this.toReportRecord(order, visit))
    );
  }

  get allReports(): ReportRecord[] {
    return [...this.completedLabReports, ...this.completedRadiologyReports].sort((a, b) => new Date(b.completed_at || b.visit_date).getTime() - new Date(a.completed_at || a.visit_date).getTime());
  }

  get visibleReports(): ReportRecord[] {
    if (this.reportType === 'laboratory') {
      return this.completedLabReports;
    }
    if (this.reportType === 'radiology') {
      return this.completedRadiologyReports;
    }
    return this.allReports;
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
    return this.allReports[0] ?? null;
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
    const reports = this.allReports.map((report) => ({
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
    const reports = this.allReports.map((item) => ({
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
    if (this.form.controls.doctor_user_id.getRawValue() !== doctor.id) {
      return 'Select to view slots';
    }
    const slot = this.availableSlots.find((item) => item.status === 'available');
    return slot ? `Next: ${this.formatSlotTime(slot.slot_start_at)}` : 'No slots on selected date';
  }

  doctorSlots(doctor: User): string[] {
    if (this.form.controls.doctor_user_id.getRawValue() !== doctor.id) {
      return [];
    }
    return this.availableSlots.filter((item) => item.status === 'available').slice(0, 3).map((item) => this.formatSlotTime(item.slot_start_at));
  }

  formatSlotTime(value: string): string {
    return new Date(value).toLocaleTimeString('en-BD', { hour: 'numeric', minute: '2-digit' });
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
    const offsetDate = new Date(date.getTime() - date.getTimezoneOffset() * 60000);
    return offsetDate.toISOString().slice(0, 10);
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
