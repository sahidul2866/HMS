export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface InventoryDashboardSummary {
  total_stock_value: string | number;
  total_items: number;
  low_stock_items: number;
  out_of_stock_items: number;
  near_expiry_items: number;
  recent_receivings: number;
  recent_issues: number;
  category_counts: Record<string, number>;
  total_stores: number;
  open_requisitions: number;
  open_transfers: number;
  store_stock_value: Record<string, string | number>;
}

export interface InventoryReport {
  low_stock_items: number;
  near_expiry_batches: number;
  expired_batches: number;
  reagent_usage_last_7_days: number;
  purchase_requests_open: number;
  open_requisitions: number;
  open_transfers: number;
  adjustment_count: number;
}

export interface InventoryItem {
  id: string;
  name: string;
  item_code?: string | null;
  barcode?: string | null;
  category_name?: string | null;
  supplier_name?: string | null;
  item_type: string;
  unit_of_measurement: string;
  stock_quantity: string | number;
  stock_value: string | number;
  reorder_level: string | number;
  storage_location?: string | null;
  is_active: boolean;
  store_balances?: InventoryStoreBalance[];
  created_at: string;
}

export interface InventoryStore {
  id: string;
  code: string;
  name: string;
  store_type: string;
  department_id?: string | null;
  parent_store_id?: string | null;
  department_name?: string | null;
  location?: string | null;
  allow_sub_store_transfers: boolean;
  description?: string | null;
  is_active: boolean;
  current_stock_value: string | number;
  total_items: number;
  low_stock_items: number;
  created_at: string;
}

export interface InventoryStoreBalance {
  id: string;
  store_id: string;
  store_name: string;
  store_type: string;
  department_name?: string | null;
  item_id: string;
  item_name: string;
  item_code?: string | null;
  category_name?: string | null;
  supplier_name?: string | null;
  quantity_on_hand: string | number;
  reserved_quantity: string | number;
  available_quantity: string | number;
  reorder_level: string | number;
  minimum_stock_level: string | number;
  maximum_stock_level: string | number;
  location?: string | null;
  stock_status: string;
  expiry_status?: string | null;
}

export interface StockReceiving {
  id: string;
  item_id: string;
  store_id?: string | null;
  supplier_id?: string | null;
  invoice_number?: string | null;
  received_date: string;
  department?: string | null;
  batch_no?: string | null;
  expiry_date?: string | null;
  quantity: string | number;
  unit_cost: string | number;
  total_cost: string | number;
  item_name?: string | null;
  store_name?: string | null;
  supplier_name?: string | null;
  created_at: string;
}

export interface StockIssue {
  id: string;
  item_id: string;
  store_id?: string | null;
  batch_id?: string | null;
  department?: string | null;
  requestor?: string | null;
  purpose?: string | null;
  patient_id?: string | null;
  visit_id?: string | null;
  quantity: string | number;
  issue_date: string;
  item_name?: string | null;
  store_name?: string | null;
  batch_no?: string | null;
  created_at: string;
}

export interface StockTransfer {
  id: string;
  item_id: string;
  source_store_id?: string | null;
  destination_store_id?: string | null;
  source_location?: string | null;
  destination_location?: string | null;
  quantity: string | number;
  requested_quantity?: string | number | null;
  approved_quantity?: string | number | null;
  issued_quantity?: string | number | null;
  received_quantity?: string | number | null;
  transfer_date: string;
  status: string;
  note?: string | null;
  item_name?: string | null;
  source_store_name?: string | null;
  destination_store_name?: string | null;
  created_at: string;
}

export interface StockAdjustment {
  id: string;
  item_id: string;
  store_id?: string | null;
  adjustment_type: string;
  quantity_change: string | number;
  reason?: string | null;
  note?: string | null;
  status: string;
  item_name?: string | null;
  store_name?: string | null;
  created_at: string;
}

export interface InventoryRequisition {
  id: string;
  item_id: string;
  source_store_id?: string | null;
  destination_store_id: string;
  department?: string | null;
  requested_quantity: string | number;
  approved_quantity?: string | number | null;
  issued_quantity?: string | number | null;
  priority: string;
  required_date?: string | null;
  reason?: string | null;
  status: string;
  remarks?: string | null;
  item_name?: string | null;
  source_store_name?: string | null;
  destination_store_name?: string | null;
  requested_by_name?: string | null;
  approved_by_name?: string | null;
  created_at: string;
}

export interface Supplier {
  id: string;
  name: string;
  contact_person?: string | null;
  phone?: string | null;
  email?: string | null;
  rating?: number | null;
  is_active: boolean;
}

export interface Reagent {
  id: string;
  reagent_code: string;
  name: string;
  category: string;
  manufacturer?: string | null;
  supplier_name?: string | null;
  storage_condition?: string | null;
  closed_balance?: string | number | null;
  status: string;
}

export interface PurchaseRequest {
  id: string;
  item_name?: string | null;
  supplier_name?: string | null;
  department?: string | null;
  requested_quantity: string | number;
  priority: string;
  status: string;
  expected_date?: string | null;
  created_at: string;
}
