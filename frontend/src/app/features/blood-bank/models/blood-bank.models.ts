export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface BloodBankDashboard {
  available_units_by_group: Record<string, number>;
  available_components_by_group: Record<string, Record<string, number>>;
  low_stock_groups: string[];
  near_expiry_units: number;
  expired_units: number;
  pending_donor_screening: number;
  pending_crossmatch_requests: number;
  pending_issue_requests: number;
  issued_units: number;
  discarded_units: number;
  emergency_requests: number;
  unsafe_units_blocked: number;
}

export interface BloodDonor {
  id: string;
  donor_number: string;
  name: string;
  date_of_birth?: string | null;
  age?: number | null;
  gender?: string | null;
  blood_group?: string | null;
  phone?: string | null;
  address?: string | null;
  last_donation_date?: string | null;
  eligibility_status: string;
  medical_screening_status: string;
  remarks?: string | null;
  donation_count?: number;
}

export interface BloodUnit {
  id: string;
  unit_number: string;
  blood_group: string;
  rh_factor?: string | null;
  component_type: string;
  collection_date?: string | null;
  expiry_date?: string | null;
  volume_ml?: number | null;
  storage_location_id?: string | null;
  storage_location_name?: string | null;
  status: string;
  testing_status: string;
  donor_id?: string | null;
  current_patient_id?: string | null;
  remarks?: string | null;
}

export interface BloodRequest {
  id: string;
  request_number: string;
  patient_id: string;
  patient_name?: string | null;
  blood_group: string;
  component_type: string;
  quantity_units: number;
  urgency: string;
  indication?: string | null;
  required_at?: string | null;
  diagnosis?: string | null;
  department_name?: string | null;
  status: string;
  payment_status?: string | null;
  remarks?: string | null;
}

export interface StorageLocation {
  id: string;
  code: string;
  name: string;
  location_type: string;
  parent_location_id?: string | null;
  temperature_min?: string | number | null;
  temperature_max?: string | number | null;
  current_temperature?: string | number | null;
  remarks?: string | null;
}

export interface BloodBankReport {
  report_type: string;
  generated_at: string;
  rows: Array<Record<string, unknown>>;
  totals: Record<string, unknown>;
}

export type BloodDonorPayload = Partial<BloodDonor> & { name: string };
export type ScreeningPayload = Record<string, unknown> & { donor_id: string; eligibility_result: string };
export type CollectionPayload = Record<string, unknown> & { donor_id: string; blood_group: string };
export type TestPayload = Record<string, unknown> & { unit_id: string; test_name: string; status: string };
export type ComponentPayload = Record<string, unknown> & { source_unit_id: string; component_type: string; expiry_date: string };
export type RequestPayload = Record<string, unknown> & { patient_id: string; blood_group: string; component_type: string; quantity_units: number };
export type CrossmatchPayload = Record<string, unknown> & { request_id: string; unit_id: string; patient_blood_group: string; result: string; compatibility_status: string };
export type IssuePayload = Record<string, unknown> & { request_id: string; unit_id: string };
export type ReturnPayload = Record<string, unknown> & { issue_id: string; decision: string };
export type DiscardPayload = Record<string, unknown> & { unit_id: string; reason: string };
export type TransfusionPayload = Record<string, unknown> & { issue_id: string; status: string };

