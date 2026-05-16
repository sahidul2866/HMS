import { Role, User } from '../../../core/models/auth.models';

export interface CreateUserPayload {
  username: string;
  email: string;
  full_name: string;
  password: string;
  role_codes: string[];
  direct_permission_codes: string[];
  branch_id?: string | null;
  department_id?: string | null;
  patient_id?: string | null;
  is_active: boolean;
  opd_consultation_fee?: number;
  opd_follow_up_fee?: number;
  opd_follow_up_days?: number;
  opd_prescription_header_name?: string | null;
  opd_prescription_header_degrees?: string | null;
  opd_prescription_header_specialty?: string | null;
  opd_prescription_header_workplace?: string | null;
  opd_prescription_header_chamber?: string | null;
  opd_prescription_header_phone?: string | null;
  opd_prescription_header_address?: string | null;
}

export interface UpdateUserOPDSettingsPayload {
  opd_consultation_fee: number;
  opd_follow_up_fee: number;
  opd_follow_up_days: number;
  opd_prescription_header_name?: string | null;
  opd_prescription_header_degrees?: string | null;
  opd_prescription_header_specialty?: string | null;
  opd_prescription_header_workplace?: string | null;
  opd_prescription_header_chamber?: string | null;
  opd_prescription_header_phone?: string | null;
  opd_prescription_header_address?: string | null;
}

export interface CreateRolePayload {
  code: string;
  name: string;
  description?: string | null;
  is_doctor_role: boolean;
  is_referral_role: boolean;
  permission_codes: string[];
}

export type AdminUser = User;
export type AdminRole = Role;

export interface ScopeAssignment {
  id: string;
  user_id?: string;
  role_id?: string;
  branch_id?: string | null;
  scope_type: string;
  scope_value?: string | null;
  scope_ref_id?: string | null;
  module?: string | null;
  status: string;
  is_primary: boolean;
  is_temporary: boolean;
  is_override: boolean;
  starts_at?: string | null;
  ends_at?: string | null;
  reason?: string | null;
  meta: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ScopeAssignmentPayload {
  user_id: string;
  scope_type: string;
  scope_value?: string | null;
  scope_ref_id?: string | null;
  module?: string | null;
  status: string;
  is_primary: boolean;
  is_temporary: boolean;
  is_override: boolean;
  starts_at?: string | null;
  ends_at?: string | null;
  reason?: string | null;
  meta: Record<string, unknown>;
}

export interface EffectiveAccess {
  user_id: string;
  roles: Array<{ id: string; code: string; name: string }>;
  permissions: string[];
  user_scopes: ScopeAssignment[];
  role_scopes: ScopeAssignment[];
  effective_scopes: Record<string, Array<Record<string, unknown>>>;
  unrestricted_modules: string[];
}
