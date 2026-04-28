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
          <div class="sticker-head">
            <strong>${escapeHtml(item.module)}</strong>
            <span>${escapeHtml(item.token)}</span>
          </div>
          <div class="barcode">${escapeHtml(item.patientNumber)}</div>
          <div class="patient">${escapeHtml(item.patientName)}</div>
          <div class="meta">${escapeHtml([item.patientNumber, item.invoiceNumber].filter(Boolean).join(' · '))}</div>
          <div class="test">${escapeHtml(item.testName)}</div>
          <div class="meta">Room ${escapeHtml(item.roomNumber || '-')} · Qty ${escapeHtml(item.quantity ?? 1)}</div>
        </section>
      `
    )
    .join('');
  const printWindow = window.open('', '_blank', 'width=900,height=700');
  if (!printWindow) {
    return false;
  }
  printWindow.document.write(`
    <html>
      <head>
        <title>${escapeHtml(title)}</title>
        <style>
          @page { size: 70mm 38mm; margin: 3mm; }
          body { margin: 0; font-family: Arial, sans-serif; color: #111827; }
          .sheet { display: grid; gap: 4mm; }
          .sticker { width: 64mm; min-height: 32mm; border: 1px solid #111827; border-radius: 2mm; padding: 2mm; break-inside: avoid; }
          .sticker-head { display: flex; justify-content: space-between; gap: 2mm; font-size: 9px; }
          .barcode { margin: 1mm 0; padding: 1mm; border: 1px dashed #111827; text-align: center; font-family: "Courier New", monospace; font-size: 18px; letter-spacing: 2px; }
          .patient { font-weight: 700; font-size: 11px; }
          .test { margin-top: 1mm; font-size: 10px; font-weight: 700; }
          .meta { font-size: 8px; color: #374151; }
        </style>
      </head>
      <body><main class="sheet">${stickerHtml}</main></body>
    </html>
  `);
  printWindow.document.close();
  printWindow.focus();
  printWindow.print();
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
