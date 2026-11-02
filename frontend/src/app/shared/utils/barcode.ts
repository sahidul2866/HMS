import JsBarcode from 'jsbarcode';

/** Standards-based bars; never substitute or remove characters from the identifier. */
export function barcodeSvg(value: string, label = value, format: 'CODE128' | 'CODE39' = 'CODE128'): string {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  JsBarcode(svg, value, {
    format,
    displayValue: true,
    text: label,
    width: 2,
    height: 58,
    margin: 20,
    fontSize: 14,
    background: '#ffffff',
    lineColor: '#111111',
  });
  svg.setAttribute('viewBox', `0 0 ${svg.getAttribute('width')} ${svg.getAttribute('height')}`);
  svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
  svg.classList.add('id-barcode-svg');
  svg.setAttribute('role', 'img');
  svg.setAttribute('aria-label', label);
  svg.setAttribute('data-barcode-format', format);
  return new XMLSerializer().serializeToString(svg);
}
