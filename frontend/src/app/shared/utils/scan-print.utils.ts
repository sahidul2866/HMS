import { barcodeSvg } from './barcode';
export interface ScanPrintPayload {
  title: string;
  code: string;
  subtitle?: string;
  lines?: string[];
  kind?: 'card' | 'wristband' | 'label' | 'document';
  themeColor?: string;
  logoUrl?: string | null;
}

export function printScanLabel(payload: ScanPrintPayload): void {
  const width = payload.kind === 'wristband' ? '280px' : payload.kind === 'label' ? '230px' : '340px';
  const lines = (payload.lines || []).map((line) => `<div class="line">${escapeHtml(line)}</div>`).join('');
  const barcode = code39Svg(payload.code);
  const color = payload.themeColor || '#0f766e';
  const logo = payload.logoUrl ? `<img class="logo" src="${escapeHtml(payload.logoUrl)}" alt="" />` : `<div class="logo fallback">H</div>`;
  const html = `
    <html>
      <head>
        <title>${escapeHtml(payload.title)}</title>
        <style>
          body { font-family: Arial, sans-serif; margin: 16px; color: #111827; }
          .card { width: ${width}; border: 1px solid #111827; border-radius: 8px; padding: 10px; border-top: 5px solid ${escapeHtml(color)}; }
          .head { display: grid; grid-template-columns: 36px 1fr; gap: 8px; align-items: center; margin-bottom: 6px; }
          .logo { width: 34px; height: 34px; object-fit: contain; border-radius: 5px; }
          .logo.fallback { display: grid; place-items: center; background: ${escapeHtml(color)}; color: white; font-weight: 800; }
          h1 { font-size: 15px; margin: 0 0 2px; }
          .subtitle { font-size: 12px; color: #475569; margin-bottom: 8px; }
          .code { font-family: "Courier New", monospace; font-size: 13px; letter-spacing: 1px; padding: 8px; border: 1px dashed #64748b; word-break: break-all; }
          .barcode { margin-top: 8px; }
          .barcode svg { width: 100%; height: 58px; }
          .line { font-size: 12px; margin-top: 4px; }
          @media print { body { margin: 0; } .card { page-break-inside: avoid; } }
        </style>
      </head>
      <body>
        <section class="card">
          <div class="head">${logo}<div><h1>${escapeHtml(payload.title)}</h1>${payload.subtitle ? `<div class="subtitle">${escapeHtml(payload.subtitle)}</div>` : ''}</div></div>
          <div class="code">${escapeHtml(payload.code)}</div>
          <div class="barcode" aria-label="Barcode">${barcode}</div>
          ${lines}
        </section>
        <script>window.print(); window.close();</script>
      </body>
    </html>`;
  const popup = window.open('', '_blank', 'width=420,height=520');
  popup?.document.write(html);
  popup?.document.close();
}

export function code39Svg(value: string): string {
  const format = /^[A-Z0-9 .$/+%\-]+$/.test(value) ? 'CODE39' : 'CODE128';
  return barcodeSvg(value, value, format);
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char] || char));
}
