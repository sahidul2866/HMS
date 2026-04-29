export interface DashboardPoint {
  label: string;
  value: number;
  date?: string;
}

export interface DashboardKpi {
  title: string;
  value: number;
  description: string;
  icon: string;
  tone: string;
  trend: number;
  format: 'money' | 'number';
  sparkline: number[];
}

export interface DashboardAlert {
  severity: string;
  title: string;
  message: string;
}

export interface DashboardActivity {
  time: string;
  module: string;
  text: string;
  tone: string;
}

export interface DashboardShortcut {
  label: string;
  route: string;
}

export interface DashboardAnalytics {
  generated_at: string;
  filters: Record<string, string | null>;
  kpis: DashboardKpi[];
  patient_analytics: {
    daily_visits: DashboardPoint[];
    opd_vs_ipd: DashboardPoint[];
    new_vs_returning: DashboardPoint[];
    department_counts: DashboardPoint[];
    doctor_load: DashboardPoint[];
    gender_distribution: DashboardPoint[];
    monthly_growth: DashboardPoint[];
  };
  appointment_analytics: {
    status_breakdown: DashboardPoint[];
    trend: DashboardPoint[];
    upcoming: { label: string; time: string; status: string }[];
  };
  bed_analytics: {
    available: number;
    occupied: number;
    occupancy_pct: number;
    ward_occupancy: DashboardPoint[];
    bed_type_status: DashboardPoint[];
    admission_trend: DashboardPoint[];
    discharge_trend: DashboardPoint[];
  };
  emergency_analytics: {
    today: number;
    priority: DashboardPoint[];
    queue: DashboardPoint[];
    average_triage_time_minutes: number;
    average_doctor_response_minutes: number;
  };
  revenue_analytics: {
    daily_revenue: DashboardPoint[];
    payment_breakdown: DashboardPoint[];
    paid_vs_pending: DashboardPoint[];
    module_breakdown: DashboardPoint[];
    outstanding_due: number;
  };
  lab_radiology_analytics: {
    lab_today: number;
    radiology_today: number;
    status: DashboardPoint[];
    test_volume: DashboardPoint[];
    average_turnaround_minutes: number;
  };
  pharmacy_inventory_analytics: {
    sales_today: number;
    top_medicines: DashboardPoint[];
    low_stock_medicines: number;
    low_stock_items: number;
    near_expiry: number;
    inventory_value: number;
    stock_consumption_trend: DashboardPoint[];
  };
  ot_analytics: {
    today_surgeries: number;
    upcoming: number;
    completed: number;
    cancelled: number;
    room_utilization: DashboardPoint[];
    surgeon_count: DashboardPoint[];
    timeline: DashboardPoint[];
    status: string;
  };
  hr_analytics: {
    total_staff: number;
    present: number;
    absent: number;
    on_leave: number;
    attendance_pct: number;
    department_staff: DashboardPoint[];
    payroll_summary: number;
    pending_leave: number;
  };
  alerts: DashboardAlert[];
  activity_feed: DashboardActivity[];
  report_shortcuts: DashboardShortcut[];
}
