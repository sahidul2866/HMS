export interface TransportDashboard {
  total_vehicles: number;
  available_ambulances: number;
  available_drivers: number;
  active_trips: number;
  pending_requests: number;
  emergency_requests: number;
  completed_trips_today: number;
  vehicles_under_maintenance: number;
  fuel_expense_today: string | number;
  delayed_trips: number;
  upcoming_scheduled_trips: number;
  readiness_alerts: number;
  by_vehicle_type: Record<string, number>;
  by_trip_status: Record<string, number>;
  by_priority: Record<string, number>;
}

export interface TransportVehicle {
  id: string;
  vehicle_number: string;
  registration_number?: string | null;
  vehicle_type: string;
  capacity?: number | null;
  equipment_available: string[];
  assigned_driver_id?: string | null;
  assigned_driver_name?: string | null;
  insurance_details?: string | null;
  insurance_expiry?: string | null;
  fitness_expiry?: string | null;
  registration_expiry?: string | null;
  fuel_type?: string | null;
  current_status: string;
  current_latitude?: string | number | null;
  current_longitude?: string | number | null;
  location_updated_at?: string | null;
  readiness_status: string;
  readiness_alerts: string[];
  qr_code?: string | null;
  remarks?: string | null;
  created_at: string;
  is_active: boolean;
}

export interface TransportDriver {
  id: string;
  employee_id?: string | null;
  employee_code?: string | null;
  driver_name: string;
  contact_number?: string | null;
  license_number: string;
  license_expiry_date?: string | null;
  license_alert?: string | null;
  assigned_vehicle_id?: string | null;
  assigned_vehicle_number?: string | null;
  shift?: string | null;
  availability_status: string;
  emergency_contact?: string | null;
  qr_code?: string | null;
  remarks?: string | null;
  created_at: string;
  is_active: boolean;
}

export interface TransportRequest {
  id: string;
  request_number: string;
  request_type: string;
  trip_type?: string | null;
  source_department?: string | null;
  patient_id?: string | null;
  patient_name?: string | null;
  patient_number?: string | null;
  staff_employee_id?: string | null;
  staff_name?: string | null;
  unknown_patient_name?: string | null;
  pickup_location: string;
  dropoff_location: string;
  required_at: string;
  urgency: string;
  priority: string;
  reason?: string | null;
  required_vehicle_type?: string | null;
  required_equipment: string[];
  attendant_required: boolean;
  transfer_reason?: string | null;
  patient_condition?: string | null;
  required_support?: string | null;
  receiving_facility?: string | null;
  responsible_doctor?: string | null;
  status: string;
  assigned_vehicle_id?: string | null;
  assigned_vehicle_number?: string | null;
  assigned_driver_id?: string | null;
  assigned_driver_name?: string | null;
  billing_required: boolean;
  billing_status: string;
  override_used: boolean;
  override_reason?: string | null;
  remarks?: string | null;
  created_at: string;
  is_active: boolean;
}

export interface TransportTrip {
  id: string;
  request_id?: string | null;
  request_number?: string | null;
  trip_number: string;
  vehicle_id: string;
  vehicle_number?: string | null;
  driver_id: string;
  driver_name?: string | null;
  patient_id?: string | null;
  patient_name?: string | null;
  patient_number?: string | null;
  staff_employee_id?: string | null;
  staff_name?: string | null;
  pickup_location: string;
  dropoff_location: string;
  scheduled_at?: string | null;
  start_time?: string | null;
  end_time?: string | null;
  distance_km: string | number;
  waiting_minutes: number;
  trip_type?: string | null;
  priority: string;
  status: string;
  location_updates: Array<Record<string, unknown>>;
  charges?: Record<string, unknown> | null;
  billing_status: string;
  qr_code?: string | null;
  remarks?: string | null;
  created_at: string;
  is_active: boolean;
}

export interface TransportSchedule {
  id: string;
  vehicle_id?: string | null;
  vehicle_number?: string | null;
  driver_id?: string | null;
  driver_name?: string | null;
  schedule_type: string;
  start_at: string;
  end_at: string;
  recurrence_rule?: string | null;
  status: string;
  purpose?: string | null;
  remarks?: string | null;
}

export interface TransportMaintenance {
  id: string;
  vehicle_id: string;
  vehicle_number?: string | null;
  maintenance_type: string;
  service_date: string;
  odometer_reading?: string | number | null;
  workshop_vendor?: string | null;
  cost: string | number;
  next_service_date?: string | null;
  parts_changed?: string | null;
  status: string;
  remarks?: string | null;
}

export interface TransportFuelLog {
  id: string;
  vehicle_id: string;
  vehicle_number?: string | null;
  fuel_date: string;
  quantity: string | number;
  fuel_cost: string | number;
  odometer_reading?: string | number | null;
  filled_by?: string | null;
  receipt_attachment?: string | null;
  expense_category: string;
  remarks?: string | null;
}

export interface TransportSetting {
  id: string;
  setting_key: string;
  setting_value: string;
  description?: string | null;
  meta?: Record<string, unknown> | null;
  is_active: boolean;
}

export interface TransportReport {
  report_type: string;
  filters: Record<string, unknown>;
  rows: Array<Record<string, unknown>>;
  totals: Record<string, unknown>;
}
