import { User } from '../../core/models/auth.models';
import { ConfigurationProfile } from '../../features/configuration/services/configuration.service';
import { OPDVisit, OPDVisitOrder } from '../../features/opd/models/opd.models';
import { buildBarcodeSvg, escapePrintHtml, renderPrintLines } from './print-layout.utils';

type SectionPlacement = 'full' | 'left' | 'right';

type PrintableSection = {
  key: string;
  label: string;
  placement: SectionPlacement;
  height: number;
};

type PrintPayload = {
  visit: OPDVisit;
  doctor?: User | null;
  layoutProfile?: ConfigurationProfile | null;
};

const DEFAULT_SECTIONS: PrintableSection[] = [
  { key: 'header', label: 'Doctor Header', placement: 'full', height: 64 },
  { key: 'patient', label: 'Patient Details', placement: 'full', height: 40 },
  { key: 'complaint', label: 'Chief Complaint', placement: 'left', height: 92 },
  { key: 'diagnosis', label: 'Diagnosis', placement: 'left', height: 82 },
  { key: 'rx', label: 'Rx', placement: 'right', height: 210 },
  { key: 'advice', label: 'Advice', placement: 'right', height: 86 },
  { key: 'follow_up', label: 'Follow-Up', placement: 'right', height: 54 },
  { key: 'signature', label: 'Signature', placement: 'full', height: 48 },
];

export function printOPDPrescription(payload: PrintPayload): boolean {
  const { visit, doctor, layoutProfile } = payload;
  const layoutPayload = layoutProfile?.payload || {};
  const paperSize = String(layoutPayload['paper_size'] || 'A5');
  const layout = String(layoutPayload['layout'] || 'two_column');
  const fontSize = Number(layoutPayload['font_size'] || 11);
  const leftColumnWidth = normalizeColumnWidth(layoutPayload['left_column_width']);
  const rightColumnWidth = 100 - leftColumnWidth;
  const showBarcode = layoutPayload['show_barcode'] !== false;
  const sections = normalizeSections(layoutPayload);
  const prescriptionOrders = visit.orders.filter((order) => order.order_type === 'prescription' && order.status !== 'cancelled');
  const fullSections = sections.filter((section) => section.placement === 'full');
  const leftSections = layout === 'single_column' ? sections.filter((section) => section.placement !== 'full') : sections.filter((section) => section.placement === 'left');
  const rightSections = layout === 'single_column' ? [] : sections.filter((section) => section.placement === 'right');
  const html = `<!doctype html>
  <html>
  <head>
    <meta charset="utf-8" />
    <title>Prescription - ${escapePrintHtml(visit.visit_number)}</title>
    <style>
      @page { size: ${escapePrintHtml(paperSize)}; margin: 7mm; }
      * { box-sizing: border-box; }
      html, body { width: 100%; height: 100%; margin: 0; padding: 0; overflow: hidden; background: #fff; color: #111827; font-family: Arial, sans-serif; font-size: ${Math.min(fontSize, 10.5)}px; }
      .sheet { height: 100vh; max-height: 100vh; overflow: hidden; padding: 4px 3px; display: grid; grid-template-rows: auto auto auto minmax(0, 1fr) auto; gap: 5px; page-break-inside: avoid; break-inside: avoid; }
      .doctor-head { display: grid; grid-template-columns: minmax(0, 1fr) minmax(160px, auto); gap: 10px; padding-bottom: 5px; border-bottom: 2px solid #111827; }
      .doctor-name { font-size: 18px; font-weight: 800; color: #111827; }
      .doctor-meta { margin-top: 1px; color: #334155; line-height: 1.2; }
      .doctor-contact { text-align: right; color: #475569; line-height: 1.2; }
      .patient-band { display: grid; grid-template-columns: 1.2fr 0.8fr 0.75fr 0.85fr; gap: 0; border: 1px solid #111827; }
      .meta { min-height: 22px; border-right: 1px solid #111827; padding: 2px 4px; }
      .meta:nth-child(4n) { border-right: 0; }
      .meta b { color: #475569; font-size: 8px; text-transform: uppercase; letter-spacing: .03em; margin-right: 4px; }
      .meta span { font-weight: 700; }
      .body-grid { min-height: 0; overflow: hidden; display: grid; grid-template-columns: ${layout === 'single_column' ? '1fr' : `${leftColumnWidth}fr ${rightColumnWidth}fr`}; gap: 0; align-content: stretch; border: 1px solid #111827; border-top: 0; }
      .column { min-height: 0; overflow: hidden; display: grid; align-content: start; gap: 5px; padding: 6px; }
      .column-left { border-right: ${layout === 'single_column' ? '0' : '1px solid #111827'}; }
      .full-row { border-left: 1px solid #111827; border-right: 1px solid #111827; padding: 4px 6px; overflow: hidden; }
      .clinical-line { display: grid; grid-template-columns: 34px minmax(0, 1fr); gap: 5px; margin-bottom: 4px; break-inside: avoid; }
      .clinical-line b { color: #111827; font-size: 9px; }
      .print-line { line-height: 1.25; margin-bottom: 1px; color: #1f2937; }
      .rx-mark { font-family: Georgia, serif; font-size: 25px; font-weight: 800; color: #111827; margin-bottom: 2px; }
      table { width: 100%; border-collapse: collapse; }
      th, td { border-bottom: 1px solid #cbd5e1; padding: 3px 3px; text-align: left; vertical-align: top; line-height: 1.2; }
      th { color: #475569; font-size: 8px; text-transform: uppercase; letter-spacing: .03em; }
      .simple-block { margin-bottom: 5px; }
      .footer { display: grid; grid-template-columns: minmax(0, 1fr) 160px; gap: 10px; align-items: end; padding-top: 7px; }
      .barcode { max-width: 180px; height: 34px; overflow: hidden; }
      .signature { text-align: center; border-top: 1px solid #111827; padding-top: 4px; color: #334155; }
      .muted { color: #64748b; }
      @media print {
        html, body { width: 100%; height: 100%; overflow: hidden; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
        .sheet { height: 100vh; max-height: 100vh; overflow: hidden; page-break-after: avoid; page-break-before: avoid; }
      }
    </style>
  </head>
  <body>
    <main class="sheet">
      ${renderDoctorHeader(visit, doctor)}
      ${renderPatientBand(visit)}
      ${fullSections.length ? `<section class="full-row">${fullSections.map((section) => renderInlineSection(section, visit, prescriptionOrders)).join('')}</section>` : ''}
      <section class="body-grid">
        <div class="column column-left">${leftSections.map((section) => renderInlineSection(section, visit, prescriptionOrders)).join('')}</div>
        ${layout === 'single_column' ? '' : `<div class="column column-right">${rightSections.map((section) => renderInlineSection(section, visit, prescriptionOrders)).join('')}</div>`}
      </section>
      <footer class="footer">
        <div>
          ${showBarcode ? `<div class="barcode">${buildBarcodeSvg(visit.visit_number, visit.visit_number)}</div>` : ''}
          <div class="muted">${escapePrintHtml(String(layoutPayload['footer_note'] || 'Please bring this prescription on follow-up.'))}</div>
        </div>
        <div class="signature">${escapePrintHtml(doctor?.opd_prescription_header_name || visit.consulting_doctor_name)}<br />Doctor Signature</div>
      </footer>
    </main>
  </body>
  </html>`;

  const iframe = document.createElement('iframe');
  iframe.style.position = 'fixed';
  iframe.style.right = '0';
  iframe.style.bottom = '0';
  iframe.style.width = '0';
  iframe.style.height = '0';
  iframe.style.border = '0';
  document.body.appendChild(iframe);
  const frameDocument = iframe.contentDocument || iframe.contentWindow?.document;
  if (!frameDocument) {
    document.body.removeChild(iframe);
    return false;
  }
  frameDocument.open();
  frameDocument.write(html);
  frameDocument.close();
  const printWindow = iframe.contentWindow;
  if (!printWindow) {
    document.body.removeChild(iframe);
    return false;
  }
  printWindow.focus();
  printWindow.print();
  setTimeout(() => document.body.removeChild(iframe), 1500);
  return true;
}

function renderDoctorHeader(visit: OPDVisit, doctor?: User | null): string {
  return `<header class="doctor-head">
    <div>
      <div class="doctor-name">${escapePrintHtml(doctor?.opd_prescription_header_name || visit.consulting_doctor_name)}</div>
      <div class="doctor-meta">${renderPrintLines(doctor?.opd_prescription_header_degrees, '', 'doctor-meta-line')}</div>
      <div class="doctor-meta">${renderPrintLines(doctor?.opd_prescription_header_specialty, '', 'doctor-meta-line')}</div>
      <div class="doctor-meta">${renderPrintLines(doctor?.opd_prescription_header_workplace, '', 'doctor-meta-line')}</div>
    </div>
    <div class="doctor-contact">
      ${renderPrintLines(doctor?.opd_prescription_header_chamber, '', 'doctor-meta-line')}
      ${doctor?.opd_prescription_header_phone ? `<div>${escapePrintHtml(doctor.opd_prescription_header_phone)}</div>` : ''}
      ${renderPrintLines(doctor?.opd_prescription_header_address, '', 'doctor-meta-line')}
    </div>
  </header>`;
}

function renderPatientBand(visit: OPDVisit): string {
  const patientName = `${visit.patient.first_name} ${visit.patient.last_name}`.trim();
  return `<section class="patient-band">
    <div class="meta"><b>Patient</b><span>${escapePrintHtml(patientName)}</span></div>
    <div class="meta"><b>Patient ID</b><span>${escapePrintHtml(visit.patient.patient_number)}</span></div>
    <div class="meta"><b>Visit</b><span>${escapePrintHtml(visit.visit_number)}</span></div>
    <div class="meta"><b>Date</b><span>${escapePrintHtml(visit.visit_date)}</span></div>
    <div class="meta"><b>Age / Gender</b><span>${escapePrintHtml([visit.patient.date_of_birth || '', visit.patient.gender || ''].filter(Boolean).join(' / ') || '-')}</span></div>
    <div class="meta"><b>Mobile</b><span>${escapePrintHtml(visit.patient.phone || '-')}</span></div>
    <div class="meta"><b>Department</b><span>${escapePrintHtml(visit.department_name)}</span></div>
    <div class="meta"><b>Doctor</b><span>${escapePrintHtml(visit.consulting_doctor_name)}</span></div>
  </section>`;
}

function renderInlineSection(section: PrintableSection, visit: OPDVisit, orders: OPDVisitOrder[]): string {
  const style = `style="min-height:${Math.max(24, Math.round(section.height * 0.58))}px"`;
  switch (section.key) {
    case 'rx':
      return `<div class="simple-block" ${style}><div class="rx-mark">Rx</div>${renderMedicineTable(orders)}</div>`;
    case 'advice':
      return renderClinicalLine('Advice', visit.follow_up_note, style);
    case 'follow_up':
      return renderClinicalLine('F/U', [visit.follow_up_date, visit.follow_up_note].filter(Boolean).join('\n'), style);
    case 'complaint':
      return renderClinicalLine('C/C', visit.chief_complaint, style);
    case 'history':
      return renderClinicalLine('H/O', visit.history_of_present_illness || visit.past_history, style);
    case 'vitals':
      return renderClinicalLine('Vitals', visit.vital_signs, style);
    case 'examination':
      return renderClinicalLine('O/E', visit.examination_note, style);
    case 'diagnosis':
      return renderClinicalLine('Dx', [visit.provisional_diagnosis, visit.final_diagnosis].filter(Boolean).join('\n'), style);
    case 'investigation':
      return renderInvestigationBlock(visit.orders.filter((order) => order.order_type === 'investigation' && order.status !== 'cancelled'), style);
    default:
      return '';
  }
}

function renderClinicalLine(label: string, value: string | null | undefined, style = ''): string {
  const content = String(value || '').trim();
  if (!content) return '';
  return `<div class="clinical-line" ${style}><b>${escapePrintHtml(label)}</b><div>${renderPrintLines(content, '')}</div></div>`;
}

function renderMedicineTable(orders: OPDVisitOrder[]): string {
  if (!orders.length) {
    return '<div class="muted">No medicines added.</div>';
  }
  return `<table>
    <thead><tr><th>Medicine</th><th>Instruction</th><th>Qty</th></tr></thead>
    <tbody>
      ${orders.map((order) => `<tr><td>${escapePrintHtml(order.item_name)}</td><td>${escapePrintHtml(order.instructions || '-')}</td><td>${escapePrintHtml(order.quantity)}</td></tr>`).join('')}
    </tbody>
  </table>`;
}

function renderInvestigationBlock(orders: OPDVisitOrder[], style = ''): string {
  if (!orders.length) return '';
  return `<div class="clinical-line" ${style}><b>Tests</b><div>
    ${orders.map((order) => `<div class="print-line">${escapePrintHtml(order.item_name)}${order.service_area ? ` (${escapePrintHtml(order.service_area)})` : ''}</div>`).join('')}
  </div></div>`;
}

function normalizeSections(payload: Record<string, unknown>): PrintableSection[] {
  const savedLabels = Array.isArray(payload['section_labels']) ? payload['section_labels'] as Array<Partial<PrintableSection> & { key?: string }> : [];
  const savedByKey = new Map(savedLabels.filter((item) => item.key).map((item) => [String(item.key), item]));
  const keys = Array.isArray(payload['sections']) ? payload['sections'].map(String) : DEFAULT_SECTIONS.map((section) => section.key);
  const structural = new Set(['header', 'patient', 'signature']);
  return keys
    .filter((key) => !structural.has(key))
    .map((key) => {
      const fallback = DEFAULT_SECTIONS.find((section) => section.key === key) || { key, label: key, placement: 'full' as SectionPlacement, height: 80 };
      const saved = savedByKey.get(key);
      return { key, label: String(saved?.label || fallback.label), placement: normalizePlacement(saved?.placement || fallback.placement), height: normalizeHeight(saved?.height || fallback.height) };
    });
}

function normalizePlacement(value: unknown): SectionPlacement {
  return value === 'left' || value === 'right' || value === 'full' ? value : 'full';
}

function normalizeHeight(value: unknown): number {
  const height = Number(value || 80);
  return Number.isFinite(height) ? Math.min(Math.max(Math.round(height), 34), 320) : 80;
}

function normalizeColumnWidth(value: unknown): number {
  const width = Number(value || 38);
  return Number.isFinite(width) ? Math.min(Math.max(Math.round(width), 25), 65) : 38;
}
