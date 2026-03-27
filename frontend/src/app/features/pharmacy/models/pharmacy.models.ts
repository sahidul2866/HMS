export interface PharmacyDispense {
  id: string;
  patient_id?: string | null;
  source_visit_id?: string | null;
  source_visit_order_id?: string | null;
  patient_name?: string | null;
  patient_number?: string | null;
  visit_number?: string | null;
  prescription_ref?: string | null;
  medicine_name: string;
  requested_quantity?: string | null;
  quantity: string;
  returned_quantity: string;
  remaining_quantity: string;
  unit_price: string;
  total_price: string;
  status: string;
  note?: string | null;
  return_note?: string | null;
  dispensed_at: string;
  dispensed_by_name?: string | null;
}

export interface DispensePayload {
  patient_id?: string | null;
  branch_id?: string | null;
  source_visit_id?: string | null;
  source_visit_order_id?: string | null;
  prescription_ref?: string | null;
  medicine_name: string;
  quantity: number;
  unit_price: number;
  note?: string | null;
}

export interface PharmacyPendingPrescription {
  order_id: string;
  visit_id: string;
  visit_number: string;
  patient_id: string;
  patient_number: string;
  patient_name: string;
  doctor_name: string;
  visit_date: string;
  visit_status: string;
  item_name: string;
  quantity: string;
  dispensed_quantity: string;
  remaining_quantity: string;
  instructions?: string | null;
  chief_complaint?: string | null;
  diagnosis?: string | null;
}

export interface PharmacySummary {
  total_dispenses: number;
  today_dispenses: number;
  pending_prescriptions: number;
  billed_prescriptions: number;
  partial_dispenses: number;
  returned_dispenses: number;
}

export interface PharmacyReturnPayload {
  quantity: number;
  note?: string | null;
}
