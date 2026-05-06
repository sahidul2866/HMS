export interface InvestigationWorkItem {
  order_id: string;
  visit_id: string;
  visit_number: string;
  visit_date: string;
  patient_id: string;
  patient_number: string;
  patient_name: string;
  consulting_doctor_name: string;
  service_area: string;
  item_name: string;
  room_number?: string | null;
  quantity: string;
  instructions?: string | null;
  chief_complaint?: string | null;
  diagnosis?: string | null;
  status: string;
  sample_note?: string | null;
  sample_collected_at?: string | null;
  result_text?: string | null;
  completed_at?: string | null;
  verified_at?: string | null;
  has_pacs_link?: boolean;
  pacs_study_uid?: string | null;
}

export interface RadiologyViewerPayload {
  order_id: string;
  study_uid: string;
  viewer_url: string;
}

export interface RadiologyReportPayload {
  order_id: string;
  findings: string;
  impression?: string | null;
  recommendation?: string | null;
}

export interface PACSLinkPayload {
  order_id: string;
  study_uid: string;
  orthanc_study_id?: string | null;
  accession_number?: string | null;
  dicom_patient_id?: string | null;
  series_uid?: string | null;
  viewer_url?: string | null;
  status?: string;
}

export interface InvestigationResultPayload {
  status: string;
  sample_note?: string | null;
  result_text?: string | null;
}

export interface RadiologySummary {
  total_orders: number;
  pending_orders: number;
  ready_orders: number;
  in_progress_orders: number;
  completed_orders: number;
  verified_orders: number;
}

export interface RadiologySimulatorMachine {
  code: string;
  name: string;
  modality: string;
  status: string;
  sample_source: string;
}

export interface RadiologySimulatorFeedPayload {
  machine_code: string;
  note?: string | null;
}

export interface RadiologySimulatorFeedResponse {
  order_id: string;
  machine_code: string;
  machine_name: string;
  study_uid: string;
  orthanc_study_id?: string | null;
  viewer_url: string;
  note?: string | null;
}
