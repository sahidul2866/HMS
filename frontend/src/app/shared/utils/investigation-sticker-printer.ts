import { buildBarcodeSvg } from './print-layout.utils';

export interface InvestigationSticker {
  module: string;
  token: string;
  patientNumber: string;
  patientName: string;
  invoiceNumber?: string | null;
  testName: string;
  roomNumber?: string | null;
  quantity?: string | number | null;
}

export function printInvestigationStickers(stickers: InvestigationSticker[], title = 'Investigation Stickers'): boolean {
  if (!stickers.length) {
    return true;
  }
  const stickerHtml = stickers
    .map(
      (item) => `
        <section class="sticker">
          <header class="sticker-head">
            <strong>${escapeHtml(item.module)}</strong>
            <span>${escapeHtml(item.token)}</span>
          </header>
          <div class="barcode-wrap">${buildBarcodeSvg(`${item.patientNumber}-${item.token}`, item.patientNumber)}</div>
          <div class="patient">${escapeHtml(item.patientName)}</div>
          <div class="test">${escapeHtml(item.testName)}</div>
          <div class="meta-row">
            <span>${escapeHtml(item.invoiceNumber || '-')}</span>
            <span>Room ${escapeHtml(item.roomNumber || '-')}</span>
            <span>Qty ${escapeHtml(item.quantity ?? 1)}</span>
          </div>
        </section>
      `
    )
    .join('');
  const iframe = document.createElement('iframe');
  iframe.style.position = 'fixed';
  iframe.style.right = '0';
  iframe.style.bottom = '0';
  iframe.style.width = '0';
  iframe.style.height = '0';
  iframe.style.border = '0';
  iframe.style.visibility = 'hidden';
  iframe.srcdoc = `
    <html>
      <head>
        <title>${escapeHtml(title)}</title>
        <style>
          @page { size: 70mm 38mm; margin: 2mm; }
          * { box-sizing: border-box; }
          body { margin: 0; font-family: Inter, Arial, sans-serif; color: #0f172a; background: #ffffff; }
          .sheet { display: block; }
          .sticker {
            width: 66mm;
            height: 33.5mm;
            border: 1px solid #1e3a8a;
            border-radius: 2.5mm;
            padding: 2mm;
            overflow: hidden;
            page-break-inside: avoid;
            break-inside: avoid-page;
          }
          .sticker + .sticker { page-break-before: always; }
          .sticker-head { display: flex; justify-content: space-between; align-items: center; font-size: 9px; font-weight: 700; color: #1e3a8a; text-transform: uppercase; letter-spacing: .3px; margin-bottom: 1mm; }
          .barcode-wrap { margin-bottom: 1mm; }
          .barcode-wrap .id-barcode-svg { width: 100%; height: 12.5mm; border: 1px dashed #94a3b8; border-radius: 1.5mm; }
          .patient { font-size: 10.5px; font-weight: 700; margin-bottom: .6mm; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
          .test { font-size: 9px; font-weight: 600; margin-bottom: .6mm; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
          .meta-row { display: flex; gap: 1mm; justify-content: space-between; font-size: 7.2px; color: #334155; }
        </style>
      </head>
      <body><main class="sheet">${stickerHtml}</main></body>
    </html>
  `;
  document.body.appendChild(iframe);
  iframe.onload = () => {
    const printWindow = iframe.contentWindow;
    if (!printWindow) {
      document.body.removeChild(iframe);
      return;
    }
    printWindow.focus();
    printWindow.print();
    window.setTimeout(() => {
      if (iframe.parentNode) {
        iframe.parentNode.removeChild(iframe);
      }
    }, 300);
  };
  return true;
}

function escapeHtml(value: unknown): string {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
