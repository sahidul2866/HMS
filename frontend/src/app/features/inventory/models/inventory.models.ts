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
}

export interface InventoryReport {
  low_stock_items: number;
  near_expiry_batches: number;
  expired_batches: number;
  reagent_usage_last_7_days: number;
  purchase_requests_open: number;
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
