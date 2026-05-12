export interface ScanResolvedRecord {
  record_type: string;
  record_id: string;
  display: string;
  status?: string | null;
  route?: string | null;
  module: string;
  permission: string;
  safety: Record<string, unknown>;
  data: Record<string, unknown>;
}

export interface ScanResolveResponse {
  success: boolean;
  message: string;
  code: string;
  match_count: number;
  records: ScanResolvedRecord[];
  action?: string | null;
}

export interface ScanResolveRequest {
  code: string;
  module?: string;
  action?: string;
  expected_record_type?: string;
  expected_patient_id?: string;
  device_label?: string;
  location_label?: string;
}

export interface ScanCode {
  id: string;
  code_value: string;
  code_type: string;
  purpose: string;
  record_type: string;
  record_id: string;
  display_value?: string | null;
  expires_at?: string | null;
}

export interface ScanSetting {
  id: string;
  setting_key: string;
  setting_value: Record<string, unknown>;
  department_id?: string | null;
}

