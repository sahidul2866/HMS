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
  internal_referral_user_id?: string | null;
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

export interface BillingPayment {
  id: string;
  invoice_id: string;
  patient_id: string;
  receipt_number: string;
  payment_method: string;
  amount: string;
  note?: string | null;
  received_at: string;
  collected_by_user_id: string;
  created_at: string;
}

export interface BillingPaymentPayload {
  amount: number;
  payment_method: 'cash' | 'card' | 'mobile_banking' | 'bank_transfer';
  note?: string | null;
  received_at?: string | null;
}

export interface BillingRefund {
  id: string;
  invoice_id: string;
  payment_id?: string | null;
  patient_id: string;
  refund_number: string;
  amount: string;
  reason: string;
  refunded_at: string;
  refunded_by_user_id: string;
  created_at: string;
}

export interface BillingRefundPayload {
  amount: number;
  payment_id?: string | null;
  reason: string;
  refunded_at?: string | null;
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
  internal_referral_user_id?: string | null;
  referred_doctor_name?: string | null;
  status: string;
  payment_status: string;
  void_reason?: string | null;
  voided_at?: string | null;
  sub_total: string;
  discount_percentage: string;
  discount_amount: string;
  total_amount: string;
  paid_amount: string;
  refunded_amount: string;
  due_amount: string;
  referred_doctor_amount: string;
  note?: string | null;
  created_at: string;
  items: BillingInvoiceItem[];
  payments: BillingPayment[];
  refunds: BillingRefund[];
}

export interface BillingInvoiceListItem {
  id: string;
  invoice_number: string;
  patient_id: string;
  patient: Patient;
  internal_referral_user_id?: string | null;
  status: string;
  payment_status: string;
  paid_amount: string;
  refunded_amount: string;
  due_amount: string;
  total_amount: string;
  referred_doctor_name?: string | null;
  created_at: string;
}

export interface BillingInvoiceFilters {
  q?: string;
  internal_referral_user_id?: string;
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
  internal_referral_user_id?: string | null;
  referred_doctor_name: string;
  invoice_count: number;
  net_amount: string;
  referred_doctor_amount: string;
}

export interface BillingInvoiceVoidPayload {
  reason: string;
}
