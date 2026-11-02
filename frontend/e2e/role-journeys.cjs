/* Visit every parameterless frontend route as each seeded role. Local dev app only.
 * Prereq: backend/scripts/mint_role_tokens.py wrote HMS_ROLE_TOKENS (default /tmp/hms-role-tokens.json).
 * Allowed routes must render without errors; forbidden routes must bounce to /profile. */
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');
const base = process.env.HMS_E2E_BASE_URL || 'http://localhost:4200';
const output = process.env.HMS_E2E_ARTIFACTS || '/tmp/hms-role-journeys';
const tokensFile = process.env.HMS_ROLE_TOKENS || '/tmp/hms-role-tokens.json';
const only = (process.env.HMS_ROLES || '').split(',').filter(Boolean);
const concurrency = Number(process.env.HMS_CONCURRENCY || 4);
if (!['localhost', '127.0.0.1'].includes(new URL(base).hostname)) throw Error('Local app only.');

function routeTable() {
  const source = fs.readFileSync(path.join(__dirname, '../src/app/app.routes.ts'), 'utf8');
  const chunks = source.split(/\bpath:\s*'/).slice(1);
  const routes = [];
  for (const chunk of chunks) {
    const route = chunk.slice(0, chunk.indexOf("'"));
    const entry = chunk.slice(0, 1200);
    const next = entry.search(/\bpath:\s*'/);
    const body = next > 0 ? entry.slice(0, next) : entry;
    const match = body.match(/permissions:\s*\[([^\]]*)\]/);
    const anyOf = /permissionMode:\s*'any'/.test(body);
    if (!route || ['auth', 'login', 'patient-register'].includes(route) || route.includes(':') || route === '**' || /redirectTo/.test(body.split('}')[0])) continue;
    routes.push({ route, anyOf, permissions: match ? [...match[1].matchAll(/'([^']+)'/g)].map(m => m[1]) : [] });
  }
  return [...new Map(routes.map(r => [r.route, r])).values()];
}

async function runRole(browser, role, info, routes) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, timezoneId: 'Asia/Dhaka' });
  // HMS_API_PROXY=127.0.0.1:8001 sends the app's API calls to another local backend (for example one running newer code).
  if (process.env.HMS_API_PROXY) {
    if (!/^(127\.0\.0\.1|localhost):\d+$/.test(process.env.HMS_API_PROXY)) throw Error('HMS_API_PROXY must be a local host:port.');
    await context.route(/\/\/(localhost|127\.0\.0\.1):8000\/api\/v1\//, r => r.continue({ url: r.request().url().replace(/\/\/(localhost|127\.0\.0\.1):8000/, '//' + process.env.HMS_API_PROXY) }));
  }
  await context.addInitScript(token => { try { localStorage.setItem('hms.accessToken', token); } catch {} }, info.token);
  const page = await context.newPage();
  page.setDefaultTimeout(15000);
  const have = new Set(info.permissions);
  const result = { role, user: info.username, permissions: info.permissions.length, allowed: 0, denied: 0, problems: [], scopeRestricted: [], quietReads: [], menu: [] };
  let current = [];
  page.on('pageerror', e => current.push('pageerror: ' + e.message.slice(0, 160)));
  page.on('response', r => {
    if (!r.url().includes('/api/v1/')) return;
    const s = r.status(), p = new URL(r.url()).pathname.replace('/api/v1', '');
    if (s >= 500) current.push(`${s} ${r.request().method()} ${p}`);
    else if (s === 403 || s === 404) current.push(`${s} ${r.request().method()} ${p}`);
  });
  page.on('dialog', d => d.dismiss().catch(() => {}));
  await page.goto(base + '/#/dashboard', { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(2500);
  result.menu = await page.$$eval('nav a[href], aside a[href]', links => [...new Set(links.map(a => a.getAttribute('href')))].filter(Boolean)).catch(() => []);
  await page.screenshot({ path: path.join(output, role.replace(/\W+/g, '-') + '-dashboard.png') }).catch(() => {});
  for (const { route, permissions, anyOf } of routes) {
    const allowed = anyOf ? permissions.some(p => have.has(p)) : permissions.every(p => have.has(p));
    current = [];
    await page.evaluate(() => sessionStorage.removeItem('hms.tabs')).catch(() => {});
    await page.goto(`${base}/?r=${Date.now()}#/${route}`, { waitUntil: 'domcontentloaded' }).catch(e => current.push('goto: ' + e.message.slice(0, 80)));
    if (allowed) { await page.waitForLoadState('networkidle', { timeout: 12000 }).catch(() => {}); await page.waitForTimeout(250); }
    else await page.locator('.page-body').waitFor({timeout:15000}).catch(()=>{});
    const hash = await page.evaluate(() => location.hash).catch(() => '');
    const where = hash.replace(/^#\//, '').split('?')[0];
    if (allowed) {
      result.allowed++;
      const toast = await page.evaluate(() => [...document.querySelectorAll('[class*=toast],[class*=snack],[role=alert]')].map(e => e.innerText.trim().replace(/\s+/g, ' ')).filter(t => /Action needed|permission|could not|failed/i.test(t)).slice(0, 2)).catch(() => []);
      const body = await page.evaluate(() => ({ text: document.body.innerText.trim().length, overflow: document.documentElement.scrollWidth - window.innerWidth, overlay: !!document.querySelector('vite-error-overlay') })).catch(() => ({ text: 0 }));
      const issues = [];
      if (where !== route && !(route === '' )) issues.push(`redirected to /${where}`);
      if (body.overlay) issues.push('dev error overlay');
      if (body.text < 20) issues.push('blank page');
      if (body.overflow > 4) issues.push(`horizontal overflow ${body.overflow}px`);
      for (const t of toast) issues.push('TOAST: ' + t.slice(0, 120));
      // A refused lookup read with no toast is a wasted request, not a broken page; it is listed separately.
      const quiet = [...new Set(current)].filter(c => c.startsWith('403 GET') && !toast.length);
      if (quiet.length) result.quietReads.push({ route, calls: quiet });
      issues.push(...[...new Set(current)].filter(c => !quiet.includes(c)).map(c => (c.startsWith('403') ? 'api ' : '') + c));
      const explainedScope = await page.locator('.operational-access-state').isVisible().catch(()=>false);
      if(explainedScope && issues.every(issue=>issue.includes('/opd/visits') || issue.includes('Doctor-wise OPD access'))) result.scopeRestricted.push({route,issues});
      else if (issues.length) result.problems.push({ route, kind: 'allowed', issues });
    } else {
      result.denied++;
      if (where === route) result.problems.push({ route, kind: 'denied-but-open', issues: [`opened /${where} without ${permissions.filter(p => !have.has(p)).join(',')}`] });
    }
  }
  await context.close();
  return result;
}

(async () => {
  fs.mkdirSync(output, { recursive: true });
  const tokens = JSON.parse(fs.readFileSync(tokensFile, 'utf8'));
  const routes = routeTable().filter(r=>!process.env.HMS_ROLE_ROUTES || process.env.HMS_ROLE_ROUTES.split(',').includes(r.route));
  const roles = Object.keys(tokens).filter(r => !only.length || only.includes(r));
  console.log(`routes=${routes.length} roles=${roles.length}`);
  const browser = await chromium.launch({ headless: true, executablePath: process.env.HMS_CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' });
  const results = [];
  const queue = [...roles];
  await Promise.all(Array.from({ length: concurrency }, async () => {
    while (queue.length) {
      const role = queue.shift();
      const r = await runRole(browser, role, tokens[role], routes).catch(e => ({ role, fatal: e.message }));
      results.push(r);
      console.log(`${role}: allowed=${r.allowed} denied=${r.denied} problems=${r.problems?.length ?? 'FATAL ' + r.fatal} menu=${r.menu?.length}`);
    }
  }));
  await browser.close();
  fs.writeFileSync(path.join(output, 'report.json'), JSON.stringify(results, null, 1));
  const bad = results.filter(r => r.fatal || r.problems.length);
  const quiet = results.reduce((n, r) => n + (r.quietReads?.length ?? 0), 0);
  console.log(`\nquiet refused lookup reads (no toast): ${quiet} page loads`);
  console.log(`roles with problems: ${bad.length}/${results.length}; report ${output}/report.json`);
  process.exit(bad.length ? 1 : 0);
})();
