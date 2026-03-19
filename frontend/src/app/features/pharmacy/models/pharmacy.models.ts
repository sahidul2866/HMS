export interface PharmacyDispense {
  id: string;
  medicine_name: string;
  quantity: string;
  unit_price: string;
  total_price: string;
}

export interface DispensePayload {
  patient_id?: string | null;
  branch_id?: string | null;
  prescription_ref?: string | null;
  medicine_name: string;
  quantity: number;
  unit_price: number;
  note?: string | null;
}

