export interface Permission {
  id: string;
  code: string;
  module: string;
  action: string;
  description?: string;
}

export interface Role {
  id: string;
  code: string;
  name: string;
  description?: string;
  is_doctor_role?: boolean;
  is_referral_role?: boolean;
  permissions: Permission[];
}

export interface User {
  id: string;
  username: string;
  email: string;
  full_name: string;
  branch_id?: string | null;
  department_id?: string | null;
  patient_id?: string | null;
  opd_consultation_fee?: string | number | null;
  opd_follow_up_fee?: string | number | null;
  opd_follow_up_days?: number | null;
  opd_prescription_header_name?: string | null;
  opd_prescription_header_degrees?: string | null;
  opd_prescription_header_specialty?: string | null;
  opd_prescription_header_workplace?: string | null;
  opd_prescription_header_chamber?: string | null;
  opd_prescription_header_phone?: string | null;
  opd_prescription_header_address?: string | null;
  is_active: boolean;
  roles: Role[];
  direct_permissions: Permission[];
  effective_permissions: string[];
  principal_type?: 'user' | 'patient';
  last_login_at?: string | null;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  access_token_expires_at: string;
  refresh_token_expires_at: string;
}

export interface LoginResponse {
  user: User;
  tokens: TokenPair;
}

export interface ApiError {
  status: number;
  code: string;
  message: string;
  details?: unknown;
}

export interface SessionState {
  initialized: boolean;
  authenticated: boolean;
  user: User | null;
}
