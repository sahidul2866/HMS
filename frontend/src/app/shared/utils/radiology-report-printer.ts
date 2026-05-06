import { escapePrintHtml, renderPrintLines } from './print-layout.utils';

type PrintableRadiologyReport = {
  orderId: string;
  visitNumber: string;
  patientNumber: string;
  patientName: string;
  doctorName: string;
  studyName: string;
  status: string;
  findings: string;
  impression?: string | null;
  recommendation?: string | null;
  note?: string | null;
  verifiedAt?: string | null;
};

export function printRadiologyReport(payload: PrintableRadiologyReport): boolean {
  const reportNo = `RAD-${payload.orderId.slice(0, 8).toUpperCase()}`;
  const verifiedLabel = payload.verifiedAt ? new Date(payload.verifiedAt).toLocaleString() : new Date().toLocaleString();
  const html = `<!doctype html>
  <html>
  <head>
    <meta charset="utf-8" />
    <title>Radiology Report - ${escapePrintHtml(payload.patientNumber)}</title>
    <style>
      @page { size: A4; margin: 12mm; }
      * { box-sizing: border-box; }
      body { margin: 0; font-family: Inter, Arial, sans-serif; color: #0f172a; background: #fff; }
      .sheet { border: 1px solid #d8e2ee; border-radius: 12px; padding: 16px; }
      .head { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #1e40af; padding-bottom: 10px; }
      .title { font-size: 22px; font-weight: 700; color: #1e3a8a; }
      .sub { color: #475569; font-size: 12px; margin-top: 2px; }
      .flag { background: #dbeafe; color: #1e40af; padding: 6px 10px; border-radius: 999px; font-size: 11px; font-weight: 700; }
      .grid { margin-top: 12px; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px; }
      .cell { border: 1px solid #d8e2ee; border-radius: 8px; padding: 8px 10px; }
      .cell b { display: block; font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: .04em; margin-bottom: 4px; }
      .cell span { font-size: 13px; font-weight: 600; }
      .section { margin-top: 12px; border: 1px solid #d8e2ee; border-radius: 8px; padding: 10px; }
      .section h3 { margin: 0 0 6px; color: #1e3a8a; font-size: 12px; text-transform: uppercase; letter-spacing: .05em; }
      .print-line { font-size: 12px; line-height: 1.45; color: #334155; margin-bottom: 2px; }
      .footer { margin-top: 20px; display: flex; justify-content: space-between; font-size: 11px; color: #475569; }
      @media print { body { -webkit-print-color-adjust: exact; print-color-adjust: exact; } }
    </style>
  </head>
  <body>
    <main class="sheet">
      <header class="head">
        <div>
          <div class="title">Radiology Diagnostic Report</div>
          <div class="sub">Hospital Management System</div>
        </div>
        <span class="flag">${escapePrintHtml(payload.status.toUpperCase())}</span>
      </header>

      <section class="grid">
        <div class="cell"><b>Report No</b><span>${escapePrintHtml(reportNo)}</span></div>
        <div class="cell"><b>Verified At</b><span>${escapePrintHtml(verifiedLabel)}</span></div>
        <div class="cell"><b>Patient</b><span>${escapePrintHtml(payload.patientName)} (${escapePrintHtml(payload.patientNumber)})</span></div>
        <div class="cell"><b>Visit</b><span>${escapePrintHtml(payload.visitNumber)}</span></div>
        <div class="cell"><b>Consulting Doctor</b><span>${escapePrintHtml(payload.doctorName)}</span></div>
        <div class="cell"><b>Study</b><span>${escapePrintHtml(payload.studyName)}</span></div>
      </section>

      <section class="section">
        <h3>Findings</h3>
        ${renderPrintLines(payload.findings, 'Not recorded')}
      </section>
      <section class="section">
        <h3>Impression</h3>
        ${renderPrintLines(payload.impression, 'Not recorded')}
      </section>
      <section class="section">
        <h3>Recommendation</h3>
        ${renderPrintLines(payload.recommendation, 'Not recorded')}
      </section>
      <section class="section">
        <h3>Technician / Staff Note</h3>
        ${renderPrintLines(payload.note, 'Not recorded')}
      </section>

      <footer class="footer">
        <div>This report is electronically generated from Radiology workflow and PACS.</div>
        <div>Authorized by Radiology Department</div>
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

  const win = iframe.contentWindow;
  if (!win) {
    document.body.removeChild(iframe);
    return false;
  }
  win.focus();
  win.print();
  setTimeout(() => document.body.removeChild(iframe), 1500);
  return true;
}
