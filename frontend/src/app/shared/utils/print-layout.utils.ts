import { barcodeSvg } from './barcode';
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
  const source = String(value ?? '').trim() || '-';
  return barcodeSvg(source, label || source);
}
