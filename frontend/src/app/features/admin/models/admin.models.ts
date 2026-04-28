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
