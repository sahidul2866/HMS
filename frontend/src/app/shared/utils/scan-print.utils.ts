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
  const patterns: Record<string, string> = {
    '0': '101001101101', '1': '110100101011', '2': '101100101011', '3': '110110010101', '4': '101001101011',
    '5': '110100110101', '6': '101100110101', '7': '101001011011', '8': '110100101101', '9': '101100101101',
    A: '110101001011', B: '101101001011', C: '110110100101', D: '101011001011', E: '110101100101',
    F: '101101100101', G: '101010011011', H: '110101001101', I: '101101001101', J: '101011001101',
    K: '110101010011', L: '101101010011', M: '110110101001', N: '101011010011', O: '110101101001',
    P: '101101101001', Q: '101010110011', R: '110101011001', S: '101101011001', T: '101011011001',
    U: '110010101011', V: '100110101011', W: '110011010101', X: '100101101011', Y: '110010110101',
    Z: '100110110101', '-': '100101011011', '.': '110010101101', ' ': '100110101101', '$': '100100100101',
    '/': '100100101001', '+': '100101001001', '%': '101001001001', '*': '100101101101',
  };
  const normalized = `*${value.toUpperCase().replace(/[^A-Z0-9 .$/+%-]/g, '-')}*`;
  let x = 0;
  const bars: string[] = [];
  for (const char of normalized) {
    const pattern = patterns[char] || patterns['-'];
    for (const bit of pattern) {
      const width = bit === '1' ? 2 : 1;
      bars.push(`<rect x="${x}" y="0" width="${width}" height="46" fill="#111"/>`);
      x += width + 1;
    }
    x += 2;
  }
  return `<svg viewBox="0 0 ${x} 58" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">${bars.join('')}<text x="${x / 2}" y="56" text-anchor="middle" font-family="monospace" font-size="8">${escapeHtml(value)}</text></svg>`;
}

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char] || char));
}
