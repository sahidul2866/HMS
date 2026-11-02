/* Counter billing for Bangladesh: Taka and percentage discounts, part payments, bKash/Nagad proof, amount in words.
 * Posts synthetic invoices to the LOCAL dev database. HMS_API_PROXY=127.0.0.1:8001 sends the app's API calls to another local backend. */
const fs=require('node:fs/promises');
const assert=require('node:assert/strict');
const {chromium}=require('playwright');
const base=process.env.HMS_E2E_BASE_URL||'http://127.0.0.1:4200';
const output=process.env.HMS_E2E_ARTIFACTS||'/tmp/hms-billing-bangladesh';
assert(['localhost','127.0.0.1'].includes(new URL(base).hostname));
const proxy=process.env.HMS_API_PROXY;
if(proxy)assert(/^(127\.0\.0\.1|localhost):\d+$/.test(proxy),'HMS_API_PROXY must be a local host:port');
(async()=>{
 await fs.mkdir(output,{recursive:true});
 const browser=await chromium.launch({headless:true,executablePath:process.env.HMS_CHROME_PATH||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 const context=await browser.newContext({viewport:{width:1440,height:1050},timezoneId:'Asia/Dhaka'});
 if(proxy)await context.route(/\/\/(localhost|127\.0\.0\.1):8000\/api\/v1\//,r=>r.continue({url:r.request().url().replace(/\/\/(localhost|127\.0\.0\.1):8000/,'//'+proxy)}));
 const page=await context.newPage();page.setDefaultTimeout(20000);
 const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('dialog',d=>d.accept());
 const toasts=async()=>page.evaluate(()=>[...document.querySelectorAll('[class*=toast],[role=alert]')].map(e=>e.innerText.trim().replace(/\s+/g,' ')));
 async function go(route){await page.evaluate(()=>sessionStorage.removeItem('hms.tabs')).catch(()=>{});await page.goto(base+'/?bd='+Date.now()+'#'+route,{waitUntil:'networkidle'});}
 const stage=[];const step=name=>stage.push(name);
 try{
  await page.goto(base,{waitUntil:'networkidle'});
  await page.locator('#login-identity').fill(process.env.HMS_E2E_USER||'superadmin');await page.locator('#login-password').fill(process.env.HMS_E2E_PASSWORD||'Admin123!');
  await page.getByRole('button',{name:'Sign In',exact:true}).click();await page.waitForURL('**/#/dashboard');
  const token=await page.evaluate(()=>localStorage.getItem('hms.accessToken'));
  const api=(proxy?'http://'+proxy:new URL((await(await page.request.get(base+'/assets/app-config.json')).json()).apiBaseUrl).origin)+'/api/v1';
  const call=async(method,route,body)=>{const r=await page.request.fetch(api+route,{method,headers:{Authorization:'Bearer '+token},data:body});return {status:r.status(),body:await r.json().catch(()=>null)};};
  const suffix=Date.now().toString(36).slice(-6);
  const patient=(await call('POST','/patients',{first_name:'BDBill',last_name:'Synthetic'+suffix,phone:'017'+String(Date.now()).slice(-8)})).body;assert(patient?.id,'patient created');
  step('patient');
  await go('/billing/create?patientId='+patient.id);
  await page.getByRole('heading',{name:'Services and items',exact:true}).waitFor();
  await page.getByText('Browse suggested services',{exact:true}).click();
  for(let i=0;i<2;i++)await page.locator('.quick-add-btn').first().click();
  await page.getByText('Browse suggested services',{exact:true}).click();
  const rows=page.locator('.invoice-row');assert(await rows.count()>=2);
  step('items-added');
  // Item 1: flat Taka discount; typing it clears the percentage.
  const first=rows.first();
  await first.locator('summary',{hasText:'Discount'}).click();
  await first.getByLabel('Item discount percentage').fill('5');
  await first.getByLabel('Item discount in Taka').fill('10');
  assert.equal(Number(await first.getByLabel('Item discount percentage').inputValue()),0,'percentage cleared when Taka entered');
  await first.getByLabel('Item discount percentage').fill('5');
  assert.equal(Number(await first.getByLabel('Item discount in Taka').inputValue()),0,'Taka cleared when percentage entered');
  await first.getByLabel('Item discount in Taka').fill('10');
  step('item-discount');
  await page.getByRole('button',{name:'Review payment',exact:true}).click();
  await page.getByRole('heading',{name:'Review and payment',exact:true}).waitFor();
  await page.locator('.discount-settings summary').click();
  await page.getByLabel('Invoice Discount (Taka)').fill('20');
  assert.equal(Number(await page.getByLabel('Invoice Discount %').inputValue()),0);
  await page.locator('[formcontrolname=discount_reason]').fill('Management concession BD test');
  const breakdown=await page.locator('.amount-breakdown').innerText().catch(()=> '');
  await page.screenshot({path:output+'/review.png',fullPage:true});
  step('invoice-discount');
  // Part payment by bKash needs its TrxID; posting is blocked without it.
  const shown=await page.locator('text=/^BDT\\s[\\d,]+\\.\\d{2}$/').first().innerText();
  const total=Number(shown.replace(/[^\d.]/g,''));assert(total>2,'total '+shown);
  const part=Math.floor(total/2);
  await page.getByLabel('Collect Now').fill(String(part));
  await page.locator('select[formcontrolname=payment_method]').selectOption('mobile_banking');
  await page.getByLabel('Mobile banking provider').selectOption('bkash');
  assert(await page.getByRole('button',{name:'Post Invoice',exact:true}).isDisabled(),'posting is blocked without the TrxID');
  assert(/transaction ID \(TrxID\)/i.test(await page.locator('body').innerText()),'the missing TrxID is explained');
  step('trxid-required');
  await page.getByLabel('Payment reference').fill('8N7A6D5EE7'+suffix.toUpperCase());
  const [posted]=await Promise.all([page.waitForResponse(r=>r.url().endsWith('/billing/invoices')&&r.request().method()==='POST'),page.getByRole('button',{name:'Post Invoice',exact:true}).click()]);
  assert.equal(posted.status(),200,'post '+await posted.text());
  const invoice=await posted.json();
  step('posted');
  assert.equal(invoice.invoice_discount_amount,'20.00');assert(Number(invoice.item_discount_amount)>=10,'item discount');
  assert.equal(Number(invoice.discount_amount),Number(invoice.item_discount_amount)+20);
  await page.waitForURL(/due-payments|billing\/list/);await page.waitForLoadState('networkidle');
  const part1=(await call('GET','/billing/invoices/'+invoice.id)).body;
  assert.equal(part1.payment_status,'partial','part payment leaves a due');
  assert.equal(part1.payments[0].payment_provider,'bkash');assert.equal(part1.payments[0].reference_number,('8N7A6D5EE7'+suffix).toUpperCase());
  assert(/^Taka .* Only$/.test(part1.total_in_words),part1.total_in_words);
  // Due collection later at the desk, by cash.
  await go('/billing/due-payments?invoiceId='+invoice.id);
  const collect=page.locator('details.payment-panel').filter({has:page.locator('summary',{hasText:'Collect Payment'})});await collect.waitFor();if(!(await collect.evaluate(el=>el.open)))await collect.locator('summary').click();
  const form=page.locator('details.payment-panel').filter({has:page.locator('summary',{hasText:'Collect Payment'})}).locator('form');
  await form.locator('select[formcontrolname=payment_method]').selectOption('mobile_banking');
  await form.locator('select[formcontrolname=payment_provider]').selectOption('nagad');
  await form.locator('input[formcontrolname=amount]').fill('1');
  await form.getByRole('button',{name:/Collect/}).click();
  await page.waitForTimeout(500);
  assert.equal((await call('GET','/billing/invoices/'+invoice.id)).body.payments.length,1,'no receipt was recorded without the TrxID');
  step('desk-trxid-required');
  await form.locator('input[formcontrolname=reference_number]').fill('NG'+suffix.toUpperCase()+'11');
  await Promise.all([page.waitForResponse(r=>/payments$/.test(r.url())&&r.status()===200),form.getByRole('button',{name:/Collect/}).click()]);
  await page.waitForLoadState('networkidle');
  await form.locator('select[formcontrolname=payment_method]').selectOption('cash');
  const rest=await call('GET','/billing/invoices/'+invoice.id);
  const remaining=Number(rest.body.due_amount);assert(remaining>0);
  await form.locator('input[formcontrolname=amount]').fill(String(remaining));
  await Promise.all([page.waitForResponse(r=>/payments$/.test(r.url())&&r.status()===200),form.getByRole('button',{name:/Collect/}).click()]);
  await page.waitForLoadState('networkidle');
  step('paid-in-parts');
  const final=(await call('GET','/billing/invoices/'+invoice.id)).body;
  assert.equal(final.payment_status,'paid');assert.equal(final.payments.length,3);
  assert.deepEqual(final.payments.map(p=>p.payment_provider).sort(),['bkash','nagad',null].sort());
  // Receipts on the desk show provider, reference and words.
  await page.locator('details summary',{hasText:'Receipt History'}).click();
  const text=await page.locator('body').innerText();
  assert(/bKash/i.test(text)&&/Ref 8N7A6D5EE7/i.test(text),'receipt shows bKash reference');
  assert(/Taka .* Only/.test(text),'amount in words visible');
  await page.screenshot({path:output+'/desk.png',fullPage:true});
  step('receipts');
  assert.deepEqual(errors,[]);
  console.log('Bangladesh billing journey passed: '+stage.join(' > '));
 }catch(e){await page.screenshot({path:output+'/failure.png',fullPage:true}).catch(()=>{});console.error('FAILED after '+stage.join(' > ')+': '+e.message.slice(0,600));process.exitCode=1;}
 finally{await browser.close();}
})();
