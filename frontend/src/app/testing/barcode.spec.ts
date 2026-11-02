import { BinaryBitmap, HybridBinarizer, MultiFormatReader, RGBLuminanceSource } from '@zxing/library';
import { buildBarcodeSvg } from '../shared/utils/print-layout.utils';
import { code39Svg } from '../shared/utils/scan-print.utils';

async function decode(svg: string): Promise<string> {
  const url = URL.createObjectURL(new Blob([svg], { type: 'image/svg+xml' }));
  try {
    const image = new Image();
    image.src = url;
    await image.decode();
    const canvas = document.createElement('canvas');
    canvas.width = image.naturalWidth;
    canvas.height = image.naturalHeight;
    const context = canvas.getContext('2d')!;
    context.drawImage(image, 0, 0);
    const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
    const gray = new Uint8ClampedArray(canvas.width * canvas.height);
    for (let index = 0; index < gray.length; index++) gray[index] = pixels[index * 4];
    const bitmap = new BinaryBitmap(new HybridBinarizer(new RGBLuminanceSource(gray, canvas.width, canvas.height)));
    return new MultiFormatReader().decodeWithState(bitmap).getText();
  } finally { URL.revokeObjectURL(url); }
}

describe('printed hospital barcodes', () => {
  it('round-trips patient, visit, invoice, and secure identifiers through an independent decoder', async () => {
    for (const code of ['PAT-20261031-001', 'OPD-20261031100000-12ABCDEF', 'INV-20261031100000-AB12CD34', 'HMS:CARE:Ab_c-D9/2']) {
      expect(await decode(buildBarcodeSvg(code))).toBe(code);
    }
  });
  it('prints a standard Code 39 patient card without changing its identifier', async () => {
    const code = 'HMS-PATIENT-CARD-A12BCD34';
    expect(await decode(code39Svg(code))).toBe(code);
  });
  it('keeps mixed-case secure tokens intact by using Code 128', async () => {
    const code = 'HMS:patient:Ab_c9';
    expect(await decode(code39Svg(code))).toBe(code);
  });
});
