export function escapePrintHtml(value: string | number | null | undefined): string {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

export function renderPrintLines(value: string | null | undefined, fallback = '&nbsp;', className = 'print-line'): string {
  const lines = String(value ?? '')
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  return lines.length
    ? lines.map((line) => `<div class="${className}">${escapePrintHtml(line)}</div>`).join('')
    : `<div class="${className}">${fallback}</div>`;
}

export function buildBarcodeSvg(value: string | null | undefined, label?: string): string {
  const source = String(value ?? '').trim().toUpperCase() || '-';
  const encoded = `*${source}*`;
  const bits: number[] = [];

  for (const char of encoded) {
    const code = char.charCodeAt(0);
    bits.push(1, 0);
    for (let shift = 6; shift >= 0; shift -= 1) {
      bits.push((code >> shift) & 1);
    }
    bits.push(0, 1);
  }

  const quietZone = 10;
  let x = quietZone;
  let rects = '';
  for (const bit of bits) {
    const width = bit ? 3 : 1.2;
    if (bit) {
      rects += `<rect x="${x}" y="0" width="${width}" height="58" rx="0.4" />`;
    }
    x += width;
  }
  const totalWidth = x + quietZone;
  const safeLabel = escapePrintHtml(label || source);
  const safeValue = escapePrintHtml(source);

  return `
    <svg class="id-barcode-svg" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${totalWidth} 94" preserveAspectRatio="none" aria-label="${safeLabel}">
      <rect width="${totalWidth}" height="94" fill="#ffffff"/>
      <g fill="#13263a">${rects}</g>
      <text x="${totalWidth / 2}" y="74" text-anchor="middle" font-size="10" font-family="Arial, sans-serif" fill="#65758a">${safeLabel}</text>
      <text x="${totalWidth / 2}" y="88" text-anchor="middle" font-size="12" font-family="Arial, sans-serif" fill="#13263a" letter-spacing="1.4">${safeValue}</text>
    </svg>
  `;
}

