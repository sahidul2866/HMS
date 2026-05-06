import { escapePrintHtml, renderPrintLines } from './print-layout.utils';

type PrintableLabItem = {
  orderId: string;
  visitNumber: string;
  patientNumber: string;
  patientName: string;
  doctorName: string;
  testName: string;
  roomNumber?: string | null;
  sampleNote?: string | null;
  resultText?: string | null;
  verifiedAt?: string | null;
};

type ParsedRow = {
  test: string;
  result: string;
  reference: string;
};

function parseResultRows(raw: string | null | undefined): ParsedRow[] {
  const lines = String(raw ?? '')
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  return lines.map((line) => {
    const withRef = line.match(/^([^:]+):\s*(.+?)\s*\(Ref:\s*(.+)\)$/i);
    if (withRef) {
      return {
        test: withRef[1].trim(),
        result: withRef[2].trim(),
        reference: withRef[3].trim(),
      };
    }
    const basic = line.match(/^([^:]+):\s*(.+)$/);
    if (basic) {
      return {
        test: basic[1].trim(),
        result: basic[2].trim(),
        reference: '-',
      };
    }
    return {
      test: 'Observation',
      result: line,
      reference: '-',
    };
  });
}

export function printLaboratoryReport(item: PrintableLabItem): boolean {
  const rows = parseResultRows(item.resultText);
  const reportNo = `LAB-${item.orderId.slice(0, 8).toUpperCase()}`;
  const verifiedLabel = item.verifiedAt ? new Date(item.verifiedAt).toLocaleString() : new Date().toLocaleString();
  const tableRows = rows.length
    ? rows
        .map(
          (row) => `
      <tr>
        <td>${escapePrintHtml(row.test)}</td>
        <td>${escapePrintHtml(row.result)}</td>
        <td>${escapePrintHtml(row.reference)}</td>
      </tr>
    `
        )
        .join('')
    : `<tr><td colspan="3">No structured result lines available.</td></tr>`;

  const html = `<!doctype html>
  <html>
    <head>
      <meta charset="utf-8" />
      <title>Laboratory Report - ${escapePrintHtml(item.patientNumber)}</title>
      <style>
        @page { size: A4; margin: 12mm; }
        * { box-sizing: border-box; }
        html, body { margin: 0; padding: 0; font-family: Inter, Arial, sans-serif; color: #0f172a; background: #fff; }
        .sheet { width: 100%; border: 1px solid #dbe5f0; border-radius: 10px; padding: 16px; }
        .head { display: flex; justify-content: space-between; gap: 16px; border-bottom: 2px solid #1d4ed8; padding-bottom: 10px; }
        .hosp { font-size: 20px; font-weight: 700; color: #1e3a8a; }
        .sub { color: #475569; font-size: 12px; margin-top: 2px; }
        .badge { background: #dbeafe; color: #1e3a8a; font-weight: 700; font-size: 11px; padding: 6px 10px; border-radius: 999px; align-self: start; }
        .grid { margin-top: 12px; display: grid; gap: 8px; grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .meta { border: 1px solid #dbe5f0; border-radius: 8px; padding: 8px 10px; }
        .meta b { display: block; font-size: 11px; color: #64748b; margin-bottom: 3px; text-transform: uppercase; letter-spacing: .04em; }
        .meta span { font-size: 13px; font-weight: 600; color: #0f172a; }
        h2 { margin: 16px 0 8px; font-size: 14px; text-transform: uppercase; letter-spacing: .06em; color: #1e3a8a; }
        table { width: 100%; border-collapse: collapse; border: 1px solid #dbe5f0; border-radius: 8px; overflow: hidden; }
        th, td { border-bottom: 1px solid #e2e8f0; padding: 8px; text-align: left; vertical-align: top; font-size: 12px; }
        th { background: #f1f5f9; color: #334155; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; font-size: 11px; }
        .notes { margin-top: 10px; border: 1px dashed #cbd5e1; border-radius: 8px; padding: 8px 10px; }
        .print-line { font-size: 12px; line-height: 1.45; margin-bottom: 2px; color: #334155; }
        .footer { display: flex; justify-content: space-between; margin-top: 22px; color: #475569; font-size: 11px; }
        .sign { min-width: 230px; text-align: right; }
        @media print {
          body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
          .sheet { border-color: #cbd5e1; border-radius: 0; }
        }
      </style>
    </head>
    <body>
      <main class="sheet">
        <header class="head">
          <div>
            <div class="hosp">Hospital Management System</div>
            <div class="sub">Laboratory Diagnostic Report</div>
          </div>
          <span class="badge">Verified Report</span>
        </header>

        <section class="grid">
          <div class="meta"><b>Report No</b><span>${escapePrintHtml(reportNo)}</span></div>
          <div class="meta"><b>Verified At</b><span>${escapePrintHtml(verifiedLabel)}</span></div>
          <div class="meta"><b>Patient</b><span>${escapePrintHtml(item.patientName)} (${escapePrintHtml(item.patientNumber)})</span></div>
          <div class="meta"><b>Visit</b><span>${escapePrintHtml(item.visitNumber)}</span></div>
          <div class="meta"><b>Consulting Doctor</b><span>${escapePrintHtml(item.doctorName)}</span></div>
          <div class="meta"><b>Test</b><span>${escapePrintHtml(item.testName)}${item.roomNumber ? ` · Room ${escapePrintHtml(item.roomNumber)}` : ''}</span></div>
        </section>

        <h2>Results</h2>
        <table>
          <thead>
            <tr>
              <th>Test</th>
              <th>Result</th>
              <th>Reference</th>
            </tr>
          </thead>
          <tbody>${tableRows}</tbody>
        </table>

        <h2>Sample Note</h2>
        <section class="notes">${renderPrintLines(item.sampleNote, 'No sample note recorded')}</section>

        <div class="footer">
          <div>This report is generated electronically from HMS LIS workflow.</div>
          <div class="sign">Authorized by Laboratory</div>
        </div>
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
