import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const projectRoot = resolve(__dirname, '..');
const outputPath = resolve(projectRoot, 'src/assets/app-config.json');
const apiBaseUrl = process.env.HMS_API_BASE_URL || 'http://localhost:8000/api/v1';

mkdirSync(dirname(outputPath), { recursive: true });
writeFileSync(
  outputPath,
  `${JSON.stringify({ apiBaseUrl }, null, 2)}\n`,
  'utf8'
);

console.log(`Runtime API base URL written to src/assets/app-config.json: ${apiBaseUrl}`);
