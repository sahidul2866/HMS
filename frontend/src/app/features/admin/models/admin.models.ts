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
