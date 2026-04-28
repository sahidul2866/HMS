export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface PharmacyMasterEntity {
  id: string;
  name: string;
  description?: string | null;
}

export interface PharmacyMedicineType extends PharmacyMasterEntity {
  created_at?: string | null;
}

export interface PharmacyGeneric extends PharmacyMasterEntity {}

export interface PharmacyCompany {
  id: string;
  name: string;
  contact_person?: string | null;
  phone?: string | null;
  email?: string | null;
  address?: string | null;
  note?: string | null;
}

export interface PharmacyCustomer {
  id: string;
  patient_id?: string | null;
  customer_number: string;
  name: string;
  phone?: string | null;
  email?: string | null;
  address?: string | null;
  note?: string | null;
  patient_name?: string | null;
  patient_number?: string | null;
}

export interface PharmacyMedicine {
  id: string;
  medicine_type_id: string;
  generic_id: string;
  company_id: string;
  name: string;
  strength?: string | null;
  dosage_form?: string | null;
  sku?: string | null;
  barcode?: string | null;
  purchase_price: string;
  sale_price: string;
  stock_quantity: string;
  reorder_level: string;
  description?: string | null;
  medicine_type_name: string;
  generic_name: string;
  company_name: string;
}

export interface PharmacyPurchase {
  id: string;
  medicine_id: string;
  purchase_number: string;
  purchase_date: string;
  supplier_name?: string | null;
  invoice_number?: string | null;
  batch_no?: string | null;
  expiry_date?: string | null;
  quantity: string;
  bonus_quantity: string;
  unit_cost: string;
  sale_price?: string | null;
  note?: string | null;
  total_amount: string;
  medicine_name: string;
  purchased_by_name?: string | null;
}

export interface PharmacySaleItem {
  id: string;
  medicine_id: string;
  source_visit_order_id?: string | null;
  medicine_name: string;
  batch_no?: string | null;
  expiry_date?: string | null;
  quantity: string;
  returned_quantity: string;
  available_return_quantity: string;
  unit_price: string;
  line_total: string;
  note?: string | null;
}

export interface PharmacySale {
  id: string;
  customer_id: string;
  patient_id?: string | null;
  source_visit_id?: string | null;
  sale_number: string;
  sale_date: string;
  customer_name: string;
  patient_name?: string | null;
  subtotal: string;
  discount_amount: string;
  return_amount: string;
  net_payable: string;
  status: string;
  note?: string | null;
  sold_by_name?: string | null;
  items: PharmacySaleItem[];
}

export interface PharmacyReturn {
  id: string;
  sale_id: string;
  sale_item_id: string;
  customer_id: string;
  medicine_id: string;
  return_number: string;
  sale_number: string;
  customer_name: string;
  medicine_name: string;
  batch_no?: string | null;
  expiry_date?: string | null;
  returned_at: string;
  quantity: string;
  unit_price: string;
  total_amount: string;
  note?: string | null;
  returned_by_name?: string | null;
}

export interface PharmacyInvestigationSetting {
  id: string;
  category_name: string;
  test_name: string;
  code: string;
  service_area: string;
  fee: string;
  room_number?: string | null;
  normal_range?: string | null;
  unit?: string | null;
  description?: string | null;
  specimen_type?: string | null;
  turnaround_time?: string | null;
  report_header?: string | null;
  report_template?: string | null;
  report_note_template?: string | null;
  requires_report: boolean;
  is_active: boolean;
}

export interface PharmacyInvestigationItem {
  id: string;
  setting_id: string;
  source_visit_order_id?: string | null;
  test_name: string;
  setting_code: string;
  category_name: string;
  service_area: string;
  status: string;
  fee: string;
  result_text?: string | null;
  note?: string | null;
  normal_range?: string | null;
  unit?: string | null;
  description?: string | null;
  report_header?: string | null;
  report_template?: string | null;
  report_note_template?: string | null;
  requires_report: boolean;
}

export interface PharmacyInvestigation {
  id: string;
  customer_id?: string | null;
  patient_id?: string | null;
  source_visit_id?: string | null;
  investigation_number: string;
  ordered_at: string;
  status: string;
  fee: string;
  discount_amount: string;
  total_amount: string;
  report_note?: string | null;
  note?: string | null;
  report_title?: string | null;
  report_footer_note?: string | null;
  printable_schema?: string | null;
  customer_name?: string | null;
  patient_name?: string | null;
  patient_number?: string | null;
  setting_name?: string | null;
  setting_code?: string | null;
  category_name?: string | null;
  service_area?: string | null;
  test_count: number;
  items: PharmacyInvestigationItem[];
}

export interface PharmacyDashboardSummary {
  total_medicines: number;
  low_stock_medicines: number;
  total_customers: number;
  total_sales: number;
  total_returns: number;
  total_investigations: number;
}

export interface MasterPayload {
  name: string;
  description?: string | null;
}

export interface CompanyPayload {
  name: string;
  contact_person?: string | null;
  phone?: string | null;
  email?: string | null;
  address?: string | null;
  note?: string | null;
}

export interface CustomerPayload {
  patient_id?: string | null;
  name: string;
  phone?: string | null;
  email?: string | null;
  address?: string | null;
  note?: string | null;
}

export interface MedicinePayload {
  medicine_type_id: string;
  generic_id: string;
  company_id: string;
  name: string;
  strength?: string | null;
  dosage_form?: string | null;
  sku?: string | null;
  barcode?: string | null;
  purchase_price: number;
  sale_price: number;
  reorder_level: number;
  description?: string | null;
}

export interface PurchasePayload {
  medicine_id: string;
  purchase_date: string;
  supplier_name?: string | null;
  invoice_number?: string | null;
  batch_no?: string | null;
  expiry_date?: string | null;
  quantity: number;
  bonus_quantity: number;
  unit_cost: number;
  sale_price?: number | null;
  note?: string | null;
}

export interface SaleItemPayload {
  medicine_id: string;
  source_visit_order_id?: string | null;
  batch_no?: string | null;
  expiry_date?: string | null;
  quantity: number;
  unit_price?: number | null;
  note?: string | null;
}

export interface SalePayload {
  customer_id: string;
  patient_id?: string | null;
  source_visit_id?: string | null;
  sale_date: string;
  discount_amount: number;
  note?: string | null;
  items: SaleItemPayload[];
}

export interface ReturnPayload {
  sale_id: string;
  sale_item_id: string;
  returned_at: string;
  quantity: number;
  note?: string | null;
}

export interface PharmacyStockMovement {
  id: string;
  medicine_id: string;
  medicine_name: string;
  movement_type: string;
  reference_type: string;
  reference_id?: string | null;
  quantity_change: string;
  stock_before: string;
  stock_after: string;
  batch_no?: string | null;
  expiry_date?: string | null;
  unit_cost?: string | null;
  sale_price?: string | null;
  note?: string | null;
  created_at: string;
}

export interface InvestigationSettingPayload {
  category_name: string;
  test_name: string;
  code: string;
  service_area: string;
  fee: number;
  room_number?: string | null;
  normal_range?: string | null;
  unit?: string | null;
  description?: string | null;
  specimen_type?: string | null;
  turnaround_time?: string | null;
  report_header?: string | null;
  report_template?: string | null;
  report_note_template?: string | null;
  requires_report: boolean;
  is_active: boolean;
}

export interface InvestigationItemPayload {
  setting_id: string;
  source_visit_order_id?: string | null;
  status: string;
  fee?: number | null;
  result_text?: string | null;
  note?: string | null;
}

export interface InvestigationPayload {
  customer_id?: string | null;
  patient_id?: string | null;
  source_visit_id?: string | null;
  ordered_at: string;
  status: string;
  discount_amount: number;
  report_note?: string | null;
  note?: string | null;
  report_title?: string | null;
  report_footer_note?: string | null;
  printable_schema?: string | null;
  items: InvestigationItemPayload[];
}

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

export interface PharmacyDraftMedicineSuggestion {
  medicine_id: string;
  medicine_name: string;
  generic_name?: string | null;
  company_name?: string | null;
  stock_quantity: string;
  sale_price: string;
  match_reason?: string | null;
}

export interface PharmacySalesDraftItem {
  source_visit_order_id: string;
  source_label: string;
  quantity: string;
  medicine_suggestions: PharmacyDraftMedicineSuggestion[];
  instruction?: string | null;
  warning?: string | null;
}

export interface PharmacySalesDraft {
  patient_id: string;
  patient_name: string;
  customer_id?: string | null;
  source_visit_id: string;
  source_visit_number: string;
  note?: string | null;
  items: PharmacySalesDraftItem[];
  message?: string | null;
}

export interface PharmacyInvestigationDraftItem {
  source_visit_order_id: string;
  setting_id?: string | null;
  test_name: string;
  category_name?: string | null;
  service_area: string;
  fee?: string | null;
  instruction?: string | null;
  warning?: string | null;
}

export interface PharmacyInvestigationDraft {
  patient_id: string;
  patient_name: string;
  customer_id?: string | null;
  source_visit_id: string;
  source_visit_number: string;
  report_title?: string | null;
  note?: string | null;
  items: PharmacyInvestigationDraftItem[];
  message?: string | null;
}
