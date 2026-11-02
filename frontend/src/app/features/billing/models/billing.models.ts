import { Patient } from '../../patients/models/patient.models';

export interface BillingType { id: string; code: string; name: string; department: string; }

export interface BillingService {
  billing_type_id?: string | null;
  id: string;
  service_code: string;
  name: string;
  description?: string | null;
  source_module?: string | null;
  source_entity_id?: string | null;
  billing_instruction?: string | null;
  unit_price: string;
  doctor_share_percentage: string;
  max_discount_percentage?: string | null;
  max_discount_amount?: string | null;
  room_number?: string | null;
  is_active: boolean;
}

export interface CreateBillingServicePayload {
  billing_type_id?: string | null;
  branch_id?: string | null;
  service_code: string;
  name: string;
  description?: string | null;
  unit_price: number;
  doctor_share_percentage: number;
  max_discount_percentage?: number | null;
  max_discount_amount?: number | null;
  room_number?: string | null;
}

export interface UpdateBillingServiceControlsPayload {
  billing_type_id?: string | null;
  max_discount_percentage?: number | null;
  max_discount_amount?: number | null;
  doctor_share_percentage: number;
  room_number?: string | null;
  is_active?: boolean | null;
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
  billing_service_id?: string | null;
  quantity: number;
  discount_percentage: number;
  /** Flat Taka discount on the line; used instead of the percentage. */
  discount_amount?: number | null;
  source_opd_visit_order_id?: string | null;
  source_record_type?: string | null;
  source_record_id?: string | null;
  bed_charge_date?: string | null;
  carry_forward_item_id?: string | null;
  source_label?: string | null;
  source_module?: string | null;
  source_item_type?: 'billing_service' | 'medicine' | 'investigation_setting' | null;
  source_item_id?: string | null;
}

export interface CreateBillingInvoicePayload {
  billing_type_id?: string | null;
  discount_reason?: string | null;
  branch_id?: string | null;
  patient_id: string;
  source_opd_visit_id?: string | null;
  source_ipd_admission_id?: string | null;
  source_module?: string | null;
  billing_stage?: string | null;
  internal_referral_user_id?: string | null;
  discount_percentage: number;
  /** Flat Taka discount on the whole invoice; used instead of the percentage. */
  discount_amount?: number | null;
  note?: string | null;
  items: BillingInvoiceItemPayload[];
}

export interface BillingInvoicePreview {
  sub_total: string;
  item_discount_amount: string;
  discount_percentage: string;
  invoice_discount_amount: string;
  discount_amount: string;
  total_amount: string;
  referred_doctor_amount: string;
}

export interface BillingSettings {
  max_item_discount_percentage: string;
  max_item_discount_amount?: string | null;
  max_invoice_discount_percentage: string;
  max_invoice_discount_amount?: string | null;
  default_referral_percentage: string;
}

export interface BillingPayment {
  id: string;
  invoice_id: string;
  patient_id: string;
  receipt_number: string;
  payment_method: string;
  payment_provider?: string | null;
  reference_number?: string | null;
  amount: string;
  amount_in_words?: string | null;
  note?: string | null;
  received_at: string;
  collected_by_user_id: string;
  created_at: string;
}

export interface BillingPaymentPayload {
  amount: number;
  payment_method: 'cash' | 'card' | 'mobile_banking' | 'bank_transfer';
  /** bkash, nagad, rocket, upay or other, for mobile banking. */
  payment_provider?: string | null;
  /** TrxID, card approval code or bank / cheque reference. */
  reference_number?: string | null;
  note?: string | null;
  received_at?: string | null;
}

export interface BillingRefund {
  credit_amount?: string;
  refunded_by_name?: string | null;
  payment_method?: string;
  id: string;
  invoice_id: string;
  payment_id?: string | null;
  patient_id: string;
  refund_number: string;
  amount: string;
  refund_type?: 'refund' | 'return' | string;
  return_items?: Array<Record<string, unknown>> | null;
  reason: string;
  refunded_at: string;
  refunded_by_user_id: string;
  created_at: string;
}

export interface BillingRefundPayload {
  payment_method?: string;
  amount: number;
  payment_id?: string | null;
  reason: string;
  refunded_at?: string | null;
}

export interface BillingReturnPayload {
  payment_method?: string;
  items: Array<{ invoice_item_id: string; quantity: number }>;
  payment_id?: string | null;
  reason: string;
  refunded_at?: string | null;
}

export interface BillingInvoiceItem {
  net_amount?: string;
  returnable_quantity?: string;
  id: string;
  billing_service_id?: string | null;
  source_entity_id?: string | null;
  source_opd_visit_order_id?: string | null;
  source_label?: string | null;
  source_module?: string | null;
  billing_instruction?: string | null;
  service_name: string;
  quantity: string;
  unit_price: string;
  discount_percentage: string;
  discount_amount: string;
  line_total: string;
  max_discount_percentage?: string | null;
  max_discount_amount?: string | null;
  room_number?: string | null;
  doctor_share_percentage: string;
  doctor_share_amount: string;
}

export interface BillingInvoice {
  credited_amount?: string;
  net_payable_amount?: string;
  billed_by_user_id: string;
  billed_by_name?: string | null;
  billing_type_id?: string | null;
  billing_type_name?: string | null;
  billing_department?: string | null;
  discount_reason?: string | null;
  id: string;
  invoice_number: string;
  patient_id: string;
  source_opd_visit_id?: string | null;
  source_ipd_admission_id?: string | null;
  source_module?: string | null;
  billing_stage?: string | null;
  patient: Patient;
  internal_referral_user_id?: string | null;
  referred_doctor_name?: string | null;
  status: string;
  payment_status: string;
  void_reason?: string | null;
  voided_at?: string | null;
  sub_total: string;
  item_discount_amount: string;
  discount_percentage: string;
  invoice_discount_amount: string;
  discount_amount: string;
  total_amount: string;
  paid_amount: string;
  refunded_amount: string;
  due_amount: string;
  overpaid_amount?: string;
  total_in_words?: string | null;
  due_in_words?: string | null;
  referred_doctor_amount: string;
  note?: string | null;
  created_at: string;
  items: BillingInvoiceItem[];
  payments: BillingPayment[];
  refunds: BillingRefund[];
}

export interface BillingInvoiceListItem {
  credited_amount?: string;
  net_payable_amount?: string;
  id: string;
  invoice_number: string;
  patient_id: string;
  source_opd_visit_id?: string | null;
  source_ipd_admission_id?: string | null;
  source_module?: string | null;
  billing_stage?: string | null;
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

export interface BillingInvoiceSticker {
  invoice_id: string;
  invoice_number: string;
  invoice_item_id: string;
  patient_id: string;
  patient_number: string;
  patient_name: string;
  item_name: string;
  source_module: string;
  source_reference?: string | null;
  quantity: string;
  room_number?: string | null;
  token: string;
  barcode_value: string;
  created_at: string;
}

export interface BillingInvoiceFilters {
  q?: string;
  internal_referral_user_id?: string;
  status?: string;
  payment_status?: string;
  source_module?: string;
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

export interface BillingDraftItem {
  source_label: string;
  source_module: string;
  source_item_type?: 'billing_service' | 'medicine' | 'investigation_setting' | null;
  source_item_id?: string | null;
  billing_service_id?: string | null;
  billing_service_name?: string | null;
  quantity: string;
  discount_percentage: string;
  source_opd_visit_order_id?: string | null;
  source_record_type?: string | null;
  source_record_id?: string | null;
  bed_charge_date?: string | null;
  carry_forward_item_id?: string | null;
  warning?: string | null;
}

export interface BillingDraft {
  patient_id: string;
  patient_name: string;
  source_module: string;
  billing_stage: string;
  source_opd_visit_id?: string | null;
  source_ipd_admission_id?: string | null;
  internal_referral_user_id?: string | null;
  note?: string | null;
  message?: string | null;
  prior_invoice_count: number;
  prior_billed_amount: string;
  prior_paid_amount: string;
  prior_due_amount: string;
  items: BillingDraftItem[];
}
