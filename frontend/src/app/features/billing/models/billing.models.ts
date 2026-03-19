import { Patient } from '../../patients/models/patient.models';

export interface BillingService {
  id: string;
  service_code: string;
  name: string;
  description?: string | null;
  unit_price: string;
  doctor_share_percentage: string;
  is_active: boolean;
}

export interface CreateBillingServicePayload {
  branch_id?: string | null;
  service_code: string;
  name: string;
  description?: string | null;
  unit_price: number;
  doctor_share_percentage: number;
}

export interface ReferredDoctor {
  id: string;
  doctor_code: string;
  full_name: string;
  specialty?: string | null;
  phone?: string | null;
  email?: string | null;
  is_active: boolean;
}

export interface CreateReferredDoctorPayload {
  branch_id?: string | null;
  doctor_code: string;
  full_name: string;
  specialty?: string | null;
  phone?: string | null;
  email?: string | null;
}

export interface BillingInvoiceItemPayload {
  billing_service_id: string;
  quantity: number;
}

export interface CreateBillingInvoicePayload {
  branch_id?: string | null;
  patient_id: string;
  referred_doctor_id?: string | null;
  referred_doctor_name?: string | null;
  discount_percentage: number;
  note?: string | null;
  items: BillingInvoiceItemPayload[];
}

export interface BillingInvoicePreview {
  sub_total: string;
  discount_percentage: string;
  discount_amount: string;
  total_amount: string;
  referred_doctor_amount: string;
}

export interface BillingInvoiceItem {
  id: string;
  billing_service_id: string;
  service_name: string;
  quantity: string;
  unit_price: string;
  line_total: string;
  doctor_share_percentage: string;
  doctor_share_amount: string;
}

export interface BillingInvoice {
  id: string;
  invoice_number: string;
  patient_id: string;
  patient: Patient;
  referred_doctor_id?: string | null;
  referred_doctor_name?: string | null;
  status: string;
  void_reason?: string | null;
  voided_at?: string | null;
  sub_total: string;
  discount_percentage: string;
  discount_amount: string;
  total_amount: string;
  referred_doctor_amount: string;
  note?: string | null;
  created_at: string;
  items: BillingInvoiceItem[];
}

export interface BillingInvoiceListItem {
  id: string;
  invoice_number: string;
  patient_id: string;
  patient: Patient;
  referred_doctor_id?: string | null;
  status: string;
  total_amount: string;
  referred_doctor_name?: string | null;
  created_at: string;
}

export interface BillingInvoiceFilters {
  q?: string;
  referred_doctor_id?: string;
  status?: string;
  date_from?: string;
  date_to?: string;
}

export interface BillingSummary {
  posted_invoice_count: number;
  void_invoice_count: number;
  gross_amount: string;
  discount_amount: string;
  net_amount: string;
  referred_doctor_amount: string;
}

export interface BillingReferralSummary {
  referred_doctor_id?: string | null;
  referred_doctor_name: string;
  invoice_count: number;
  net_amount: string;
  referred_doctor_amount: string;
}

export interface BillingInvoiceVoidPayload {
  reason: string;
}
