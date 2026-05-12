import { Patient } from '../../patients/models/patient.models';

export interface IPDSummary {
  total_admissions: number;
  active_admissions: number;
  discharged_admissions: number;
  occupied_beds: number;
  pending_orders?: number;
  pending_handovers?: number;
  discharge_planned?: number;
}

export interface IPDSettings {
  id?: string | null;
  updated_at?: string | null;
  ward_types: string[];
  room_types: string[];
  bed_types: string[];
  bed_statuses: string[];
  cleaning_statuses: string[];
  critical_care_categories: string[];
  default_bed_charges: Record<string, string | number>;
  admission_sources: string[];
  admission_types: string[];
  required_admission_fields: string[];
  admission_number_format: string;
  department_admission_rules: Record<string, unknown>;
  payment_type_rules: Record<string, unknown>;
  insurance_corporate_rules: Record<string, unknown>;
  doctor_assignment_types: string[];
  nurse_assignment_types: string[];
  max_patient_load_doctor: number;
  max_patient_load_nurse: number;
  department_staff_rules: Record<string, unknown>;
  shift_assignment_rules: Record<string, unknown>;
  on_call_assignment_rules: Record<string, unknown>;
  handover_templates: Array<Record<string, unknown>>;
  required_handover_fields: string[];
  shift_handover_timings: Record<string, string>;
  require_handover_acknowledgment: boolean;
  handover_escalation_minutes: number;
  doctor_note_templates: Array<Record<string, unknown>>;
  nursing_note_templates: Array<Record<string, unknown>>;
  vitals_config: Record<string, unknown>;
  intake_output_settings: Record<string, unknown>;
  care_plan_templates: Array<Record<string, unknown>>;
  procedure_note_templates: Array<Record<string, unknown>>;
  discharge_approval_levels: string[];
  required_discharge_summary_fields: string[];
  clearance_requirements: Record<string, boolean>;
  billing_clearance_rules: Record<string, unknown>;
  pharmacy_clearance_rules: Record<string, unknown>;
  lab_radiology_pending_order_rules: Record<string, unknown>;
  follow_up_requirements: Record<string, unknown>;
  role_permission_notes: Record<string, string[]>;
}

export interface IPDAdmission {
  id: string;
  bed_id?: string | null;
  doctor_user_id?: string | null;
  attending_doctor_user_id?: string | null;
  admission_number: string;
  admitted_at: string;
  admission_type: string;
  admission_source?: string | null;
  department_name?: string | null;
  payment_type?: string | null;
  insurance_info?: string | null;
  patient_condition?: string | null;
  ward_name: string;
  bed_number: string;
  attending_doctor_name: string;
  diagnosis?: string | null;
  daily_charge: number;
  advance_amount: number;
  status: string;
  billing_status?: string;
  discharge_status?: string;
  pharmacy_clearance_status?: string;
  lab_clearance_status?: string;
  radiology_clearance_status?: string;
  pending_orders?: number;
  pending_handovers?: number;
  due_medications?: number;
  current_shift?: string | null;
  handover_status?: string;
  active_doctors?: IPDStaffAssignment[];
  active_nurses?: IPDStaffAssignment[];
  expected_discharge_date?: string | null;
  discharged_at?: string | null;
  discharge_condition?: string | null;
  discharge_diagnosis?: string | null;
  discharge_summary?: string | null;
  discharge_note?: string | null;
  patient: Patient;
  movements: IPDAdmissionMovement[];
  created_at: string;
}

export interface IPDAdmissionMovement {
  id: string;
  movement_type: string;
  moved_at: string;
  from_ward_name?: string | null;
  from_bed_number?: string | null;
  to_ward_name?: string | null;
  to_bed_number?: string | null;
  transfer_reason?: string | null;
  remarks?: string | null;
  requested_by_user_id?: string | null;
  approved_by_user_id?: string | null;
  approved_at?: string | null;
  note?: string | null;
  moved_by_user_id: string;
}

export interface IPDBedBoardRow {
  bed_id: string;
  ward_name: string;
  room_type?: string | null;
  bed_number: string;
  bed_type: string;
  daily_rate: number;
  bed_status: string;
  board_status: string;
  patient_id?: string | null;
  patient_name?: string | null;
  patient_number?: string | null;
  admission_id?: string | null;
  admission_number?: string | null;
  department_name?: string | null;
  doctor_name?: string | null;
  nurse_name?: string | null;
  admitted_at?: string | null;
  discharge_status?: string | null;
  billing_status?: string | null;
  occupancy_hours: number;
}

export interface IPDDischargeReadiness {
  admission_id: string;
  admission_number: string;
  status: string;
  ready: boolean;
  checks: Array<{ key?: string; label: string; done: boolean; [key: string]: unknown }>;
  blockers: string[];
  discharge_summary_ready: boolean;
  final_bill_url?: string | null;
}

export interface IPDReportSummary {
  bed_occupancy: Record<string, unknown>;
  ward_census: Array<Record<string, unknown>>;
  transfer_history: IPDAdmissionMovement[];
  average_length_of_stay_days: number;
  discharge_status: Record<string, number>;
  pending_discharge: IPDAdmission[];
  department_flow: Array<Record<string, unknown>>;
}

export interface IPDBed {
  id: string;
  ward_name: string;
  bed_number: string;
  bed_type: string;
  daily_rate: number;
  status: string;
  note?: string | null;
}

export interface CreateIPDAdmissionPayload {
  patient_id: string;
  bed_id?: string | null;
  admitted_at: string;
  admission_type: string;
  admission_source?: string | null;
  department_name?: string | null;
  payment_type?: string | null;
  insurance_info?: string | null;
  patient_condition?: string | null;
  ward_name: string;
  bed_number: string;
  doctor_user_id?: string | null;
  attending_doctor_name: string;
  diagnosis?: string | null;
  daily_charge: number;
  advance_amount: number;
  expected_discharge_date?: string | null;
}

export interface CreateIPDBedPayload {
  ward_name: string;
  bed_number: string;
  bed_type: string;
  daily_rate: number;
  note?: string | null;
}

export interface TransferIPDAdmissionPayload {
  bed_id?: string | null;
  ward_name: string;
  bed_number: string;
  transfer_reason?: string | null;
  transfer_time?: string | null;
  approved_by_user_id?: string | null;
  remarks?: string | null;
  note?: string | null;
}

export interface DischargeIPDAdmissionPayload {
  discharge_condition?: string | null;
  discharge_diagnosis?: string | null;
  discharge_summary?: string | null;
  discharge_note?: string | null;
  allow_override?: boolean;
  override_reason?: string | null;
}

export interface IPDStaffAssignment {
  id: string;
  staff_user_id: string;
  staff_name: string;
  role_type: 'doctor' | 'nurse';
  assignment_type: string;
  shift_name?: string | null;
  ward_name?: string | null;
  bed_number?: string | null;
  department_name?: string | null;
  assigned_at: string;
  ended_at?: string | null;
  changed_at?: string | null;
  reason?: string | null;
  allow_override?: boolean;
  override_reason?: string | null;
  assigned_by_user_id: string;
  changed_by_user_id?: string | null;
  schedule_status?: string | null;
}

export interface IPDStaffAvailability {
  staff_user_id: string;
  staff_name: string;
  role_type: 'doctor' | 'nurse';
  employee_id?: string | null;
  employee_status?: string | null;
  department_name?: string | null;
  current_shift?: string | null;
  duty_area?: string | null;
  roster_status?: string | null;
  is_on_duty: boolean;
  is_on_leave: boolean;
  active_ipd_assignments: number;
  max_patient_load: number;
  is_overloaded: boolean;
  can_assign: boolean;
  warnings: string[];
}

export interface IPDShiftCoverage {
  shift_name: string;
  ward_name?: string | null;
  doctors_on_duty: number;
  nurses_on_duty: number;
  doctor_gap: boolean;
  nurse_gap: boolean;
  warnings: string[];
}

export interface IPDClinicalNote {
  id: string;
  note_type: string;
  title?: string | null;
  note: string;
  diagnosis?: string | null;
  treatment_plan?: string | null;
  template_key?: string | null;
  version: number;
  authored_by_user_id: string;
  authored_at: string;
}

export interface IPDNursingNote {
  id: string;
  note_type: string;
  note?: string | null;
  temperature?: string | number | null;
  pulse?: number | null;
  respiratory_rate?: number | null;
  systolic_bp?: number | null;
  diastolic_bp?: number | null;
  spo2?: number | null;
  pain_score?: number | null;
  intake_ml?: string | number | null;
  output_ml?: string | number | null;
  glucose?: string | number | null;
  fall_risk?: string | null;
  abnormal_alert: boolean;
  recorded_by_user_id: string;
  recorded_at: string;
}

export interface IPDOrder {
  id: string;
  order_type: string;
  service_area?: string | null;
  item_name: string;
  instructions?: string | null;
  quantity: string | number;
  priority: string;
  order_set_code?: string | null;
  scheduled_at?: string | null;
  frequency?: string | null;
  duration?: string | null;
  dose?: string | null;
  route?: string | null;
  status: string;
  billing_status: string;
  lab_order_id?: string | null;
  radiology_order_id?: string | null;
  discontinued_at?: string | null;
  cancelled_at?: string | null;
  ordered_by_user_id: string;
  ordered_at: string;
}

export interface IPDMedicationAdministration {
  id: string;
  order_id?: string | null;
  medicine_name: string;
  dose?: string | null;
  route?: string | null;
  frequency?: string | null;
  scheduled_at?: string | null;
  administered_at?: string | null;
  status: string;
  reason?: string | null;
  remarks?: string | null;
  allow_duplicate?: boolean;
  administered_by_user_id?: string | null;
}

export interface IPDNursingTask {
  id: string;
  admission_id: string;
  order_id?: string | null;
  assigned_nurse_user_id?: string | null;
  task_type: string;
  title: string;
  instructions?: string | null;
  ward_name?: string | null;
  bed_number?: string | null;
  shift_name?: string | null;
  due_at?: string | null;
  status: string;
  completed_at?: string | null;
  completed_by_user_id?: string | null;
  completion_note?: string | null;
}

export interface IPDVitalsTrend {
  recorded_at: string;
  temperature?: string | number | null;
  pulse?: number | null;
  respiratory_rate?: number | null;
  systolic_bp?: number | null;
  diastolic_bp?: number | null;
  spo2?: number | null;
  pain_score?: number | null;
  glucose?: string | number | null;
  abnormal_alert: boolean;
}

export interface IPDHandover {
  id: string;
  handover_type: string;
  shift_name?: string | null;
  receiver_user_id?: string | null;
  summary: string;
  pending_items?: string | null;
  precautions?: string | null;
  patient_condition?: string | null;
  active_diagnosis?: string | null;
  treatment_plan?: string | null;
  pending_orders?: string | null;
  medication_due?: string | null;
  abnormal_vitals?: string | null;
  critical_alerts?: string | null;
  discharge_tasks?: string | null;
  special_instructions?: string | null;
  sender_user_id: string;
  handed_over_at: string;
  acknowledged_at?: string | null;
  status: string;
}

export interface IPDHandoverBoard extends IPDHandover {
  admission_id: string;
  admission_number?: string | null;
  patient_name?: string | null;
  ward_name?: string | null;
  bed_number?: string | null;
}

export interface IPDTimelineEvent {
  id: string;
  event_type: string;
  title: string;
  detail?: string | null;
  source_type?: string | null;
  source_id?: string | null;
  occurred_at: string;
  actor_user_id?: string | null;
}

export interface IPDPatientWorkspace {
  admission: IPDAdmission;
  assignments: IPDStaffAssignment[];
  clinical_notes: IPDClinicalNote[];
  nursing_notes: IPDNursingNote[];
  orders: IPDOrder[];
  medications: IPDMedicationAdministration[];
  nursing_tasks: IPDNursingTask[];
  handovers: IPDHandover[];
  timeline: IPDTimelineEvent[];
}
