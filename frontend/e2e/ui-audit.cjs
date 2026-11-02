const fs = require('node:fs/promises');
const path = require('node:path');
const { chromium } = require('playwright');
const base = process.env.HMS_E2E_BASE_URL || 'http://127.0.0.1:4200';
const output = process.env.HMS_E2E_ARTIFACTS || '/tmp/hms-erp-audit';
if (!['localhost','127.0.0.1'].includes(new URL(base).hostname)) throw new Error('Use a local development app for the synthetic ERP audit.');
(async () => {
 await fs.mkdir(output,{recursive:true});
 const browser = await chromium.launch({headless:true, executablePath:process.env.HMS_CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 const page = await browser.newPage({viewport:{width:1440,height:1000}});
 const errors=[]; const pages=[];
 page.on('pageerror',error=>errors.push({type:'javascript',message:error.message}));
 page.on('response',response=>{if(response.status()>=400 && response.url().includes('/api/v1/'))errors.push({type:'http',status:response.status(),url:response.url()});});
 try {
  await page.goto(base,{waitUntil:'networkidle'});
  await page.locator('#login-identity').fill(process.env.HMS_E2E_USER || 'superadmin');
  await page.locator('#login-password').fill(process.env.HMS_E2E_PASSWORD || 'Admin123!');
  await page.getByRole('button',{name:'Sign In',exact:true}).click();
  await page.waitForURL('**/#/dashboard');
  for (const width of [1440,390]) {
   await page.setViewportSize({width,height:1000});
   for(const route of ['/patients/new','/appointments/create','/opd/visits','/opd/queue','/billing/create','/billing/list','/billing/operations','/ipd/admit','/ipd/admissions','/ipd','/ipd/settings']){
    await page.evaluate(()=>sessionStorage.removeItem('hms.tabs'));
    await page.goto(base+'/?e2e='+Date.now()+'#'+route,{waitUntil:'networkidle'});
    if(!page.url().endsWith('#'+route))throw Error('Navigation did not reach '+route);
    await page.locator('h1').first().waitFor({state:'visible'});
    await page.locator('app-global-loader .global-loader-card').waitFor({state:'hidden',timeout:20000});
    const layout = await page.evaluate(()=>({viewport:innerWidth,width:document.documentElement.scrollWidth,heading:document.querySelector('h1')?.textContent?.trim(),overflow:[...document.querySelectorAll('.page-body input, .page-body button, .page-body select')].filter(el=>{const r=el.getBoundingClientRect();return el.checkVisibility()&&r.width>0&&(r.right>innerWidth+1||r.left<0)}).slice(0,10).map(el=>({tag:el.tagName,text:el.textContent?.trim().slice(0,60),name:el.getAttribute('formcontrolname')}))}));
    const record={route,...layout};pages.push(record);console.log(JSON.stringify(record));
    await page.screenshot({path:path.join(output,`${width}${route.replaceAll('/','_')}.png`),fullPage:true});
   }
  }
 } finally {
  await fs.writeFile(path.join(output,'report.json'),JSON.stringify({pages,errors},null,2));
  await browser.close();
 }
 console.log('API/JS errors:',JSON.stringify(errors));
 if(errors.length||pages.some(page=>page.width>page.viewport+1))process.exitCode=1;
})().catch(error=>{console.error(error.message);process.exitCode=1});
