export interface PharmacyDispense {
  id: string;
  patient_id?: string | null;
  source_visit_id?: string | null;
  source_visit_order_id?: string | null;
  prescription_ref?: string | null;
  medicine_name: string;
  quantity: string;
  unit_price: string;
  total_price: string;
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
  patient_name: string;
  doctor_name: string;
  item_name: string;
  quantity: string;
  instructions?: string | null;
}
