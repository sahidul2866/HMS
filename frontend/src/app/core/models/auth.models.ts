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
  is_active: boolean;
  roles: Role[];
  direct_permissions: Permission[];
  effective_permissions: string[];
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
