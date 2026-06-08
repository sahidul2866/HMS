export interface CateringDashboard {
  total_meals_today: number;
  pending_meal_orders: number;
  under_preparation: number;
  ready_for_delivery: number;
  delivered: number;
  special_diet_patients: number;
  npo_patients: number;
  allergy_risk_patients: number;
  missed_or_delayed: number;
  stock_shortages: number;
  by_ward: Record<string, number>;
  by_diet_type: Record<string, number>;
  by_meal_type: Record<string, number>;
}

export interface CateringDietType {
  id: string;
  code: string;
  name: string;
  description?: string | null;
  is_npo: boolean;
  requires_approval: boolean;
  default_restrictions?: string | null;
  is_active: boolean;
}

export interface CateringMealPlan {
  id: string;
  diet_type_id?: string | null;
  diet_type_name?: string | null;
  name: string;
  meal_type: string;
  description?: string | null;
  ingredients?: string | null;
  allergens?: string | null;
  calories?: number | null;
  protein_grams?: string | number | null;
  billable_amount: string | number;
  inventory_item_id?: string | null;
  inventory_quantity: string | number;
  is_active: boolean;
}

export interface CateringMealSchedule {
  id: string;
  meal_type: string;
  display_name: string;
  serving_time: string;
  cutoff_minutes: number;
  sort_order: number;
  is_active: boolean;
}

export interface CateringDietOrder {
  id: string;
  branch_id?: string | null;
  patient_id: string;
  patient_name?: string | null;
  patient_number?: string | null;
  ipd_admission_id?: string | null;
  er_visit_id?: string | null;
  diet_type_id: string;
  diet_type_name: string;
  meal_plan_id?: string | null;
  meal_plan_name?: string | null;
  admission_number?: string | null;
  ward_name?: string | null;
  bed_number?: string | null;
  restrictions?: string | null;
  allergies?: string | null;
  special_instructions?: string | null;
  nutrition_notes?: string | null;
  start_at: string;
  end_at?: string | null;
  status: string;
  requires_approval: boolean;
  ordered_by_name?: string | null;
  approved_by_name?: string | null;
  approved_at?: string | null;
  created_at: string;
  is_active: boolean;
}

export interface CateringMealTask {
  id: string;
  diet_order_id: string;
  patient_id: string;
  patient_name?: string | null;
  patient_number?: string | null;
  meal_plan_id?: string | null;
  meal_number: string;
  meal_date: string;
  meal_type: string;
  due_at: string;
  ward_name?: string | null;
  bed_number?: string | null;
  diet_type_name: string;
  restrictions?: string | null;
  allergies?: string | null;
  special_instructions?: string | null;
  preparation_status: string;
  delivery_status: string;
  safety_status: string;
  safety_warnings: string[];
  override_reason?: string | null;
  prepared_by_name?: string | null;
  prepared_at?: string | null;
  delivered_by_name?: string | null;
  delivered_at?: string | null;
  received_by?: string | null;
  patient_response?: string | null;
  refusal_reason?: string | null;
  remarks?: string | null;
  billable_amount: string | number;
  inventory_status?: string | null;
  ticket_code?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface CateringStaffMeal {
  id: string;
  employee_id?: string | null;
  department_id?: string | null;
  department_name?: string | null;
  staff_name: string;
  staff_code?: string | null;
  meal_date: string;
  meal_type: string;
  eligibility_type: string;
  amount: string | number;
  status: string;
  token_code?: string | null;
  payroll_deductible: boolean;
  remarks?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface CateringSetting {
  id: string;
  setting_key: string;
  setting_value: string;
  description?: string | null;
  meta?: Record<string, unknown> | null;
  is_active: boolean;
}

export interface CateringReport {
  report_type: string;
  filters: Record<string, string>;
  rows: Array<Record<string, unknown>>;
  totals: Record<string, unknown>;
}
