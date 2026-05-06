export interface LISMachine {
  code: string;
  name: string;
  analyzer_type: string;
  protocol: string;
  host: string;
  port: number;
  status: string;
}

export interface LISQueueItem {
  order_id: string;
  visit_number: string;
  patient_number: string;
  patient_name: string;
  item_name: string;
  status: string;
}

export interface LISSimulationRequest {
  machine_code: string;
  order_id: string;
}

export interface LISSimulationResult {
  order_id: string;
  machine_code: string;
  machine_name: string;
  generated_result: string;
  sample_barcode: string;
  analytes: LISAnalyteResult[];
  completed_at: string;
}

export interface LISAnalyteResult {
  code: string;
  name: string;
  value: string;
  unit?: string | null;
  reference_range?: string | null;
  flag: 'normal' | 'high' | 'low' | string;
}
