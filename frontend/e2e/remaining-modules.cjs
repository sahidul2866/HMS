/* Local synthetic workflow: credits, diagnostic reports and product barcode handoffs. */
const fs=require('node:fs/promises');
const path=require('node:path');
const assert=require('node:assert/strict');
const {chromium}=require('playwright');
const base=process.env.HMS_E2E_BASE_URL||'http://127.0.0.1:4200';
const output=process.env.HMS_E2E_ARTIFACTS||'/tmp/hms-remaining-modules';
assert(['localhost','127.0.0.1'].includes(new URL(base).hostname));
(async()=>{
 await fs.mkdir(output,{recursive:true});
 await Promise.all(['failure.png','failed-request.json'].map(file=>fs.rm(path.join(output,file),{force:true})));
 const browser=await chromium.launch({headless:true,executablePath:process.env.HMS_CHROME_PATH||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 const page=await browser.newPage({viewport:{width:1440,height:1050}});page.setDefaultTimeout(20000);
 const checks=[],errors=[];let apiBase,token;
 page.on('pageerror',e=>errors.push(e.message));
 page.on('response',r=>{if(r.status()>=400&&r.url().includes('/api/v1/'))errors.push(`${r.status()} ${new URL(r.url()).pathname}`);});
 page.on('dialog',d=>d.accept());
 async function api(method,route,data){const response=await page.request.fetch(apiBase+route,{method,data,headers:{Authorization:'Bearer '+token}});assert(response.ok(),`${method} ${route}: ${response.status()} ${await response.text()}`);return response.json();}
 async function go(route){await page.evaluate(()=>sessionStorage.removeItem('hms.tabs'));await page.goto(base+'/?modules='+Date.now()+'#'+route,{waitUntil:'networkidle'});}
 async function capture(stage){checks.push(stage);await page.screenshot({path:path.join(output,stage+'.png'),fullPage:true});console.log(stage);}
 async function scan(code){await page.locator('.topbar .scan-trigger').click();await page.locator('#global-scan-input').fill(code);await page.locator('#global-scan-input').press('Enter');}
 try{
  await page.goto(base,{waitUntil:'networkidle'});await page.locator('#login-identity').fill(process.env.HMS_E2E_USER||'superadmin');await page.locator('#login-password').fill(process.env.HMS_E2E_PASSWORD||'Admin123!');await page.getByRole('button',{name:'Sign In',exact:true}).click();await page.waitForURL('**/#/dashboard');
  apiBase=(await(await page.request.get(base+'/assets/app-config.json')).json()).apiBaseUrl;assert(['localhost','127.0.0.1'].includes(new URL(apiBase).hostname));token=await page.evaluate(()=>localStorage.getItem('hms.accessToken'));
  const patient=await api('POST','/patients',{first_name:'ModuleBrowser',last_name:'Synthetic'+Date.now(),phone:'019'+String(Date.now()).slice(-8)});
  const service=await api('POST','/billing/services',{service_code:'RET-'+Date.now(),name:'Synthetic unused service',unit_price:100,doctor_share_percentage:0,max_discount_percentage:50});
  let bill=await api('POST','/billing/invoices',{patient_id:patient.id,items:[{billing_service_id:service.id,quantity:2}]});
  bill=await api('POST',`/billing/invoices/${bill.id}/payments`,{amount:20,payment_method:'cash'});
  await go('/billing/list?invoiceId='+bill.id);await page.getByRole('button',{name:'Payments and returns',exact:true}).click();await page.locator('summary').filter({hasText:/^Return Billing$/}).click();
  const form=page.locator('form').filter({has:page.getByRole('button',{name:'Post Return Billing',exact:true})});
  await form.locator('[formcontrolname=quantity]').first().fill('1');await form.locator('[formcontrolname=reason]').fill('Synthetic unused charge cancelled');
  const posted=page.waitForResponse(r=>r.url().endsWith(`/billing/invoices/${bill.id}/return`)&&r.request().method()==='POST');
  await form.getByRole('button',{name:'Post Return Billing',exact:true}).click();const response=await posted;assert(response.ok(),await response.text());bill=await response.json();
  assert.equal(Number(bill.due_amount),80);assert.equal(Number(bill.paid_amount),20);assert.equal(Number(bill.refunds[0].amount),0);assert.equal(Number(bill.refunds[0].credit_amount),100);await capture('unpaid-credit-without-cash-payout');
  const catalog=await api('GET','/billing/services');
  for(const module of ['laboratory','radiology']){
   const config=catalog.find(s=>[module,module==='laboratory'?'lab':module].includes(s.source_module)&&Number(s.unit_price)>0);assert(config,`Missing ${module} catalog item`);
   const invoice=await api('POST','/billing/invoices',{patient_id:patient.id,source_module:module,items:[{billing_service_id:config.id,quantity:1,source_module:config.source_module,source_label:config.name}]});
   const work=await api('GET',`/${module}/worklist`);const order=work.find(row=>row.visit_id===invoice.source_opd_visit_id);assert(order,`No ${module} handoff`);
   await go(`/${module}/workbench/${order.order_id}`);
   await page.locator('[formcontrolname=status]').selectOption('completed');await page.locator('[formcontrolname=sample_note]').fill('Synthetic module specimen note');await page.locator('[formcontrolname=result_text]').fill(`Synthetic ${module} findings survive reload`);
   const saved=page.waitForResponse(r=>r.url().endsWith(`/${module}/worklist/${order.order_id}`)&&r.request().method()==='PUT');await page.getByRole('button',{name:module==='laboratory'?'Save Laboratory Update':'Save Radiology Update',exact:true}).click();assert((await saved).ok());
   await go(`/${module}/workbench/${order.order_id}`);assert.equal(await page.locator('[formcontrolname=result_text]').inputValue(),`Synthetic ${module} findings survive reload`);assert.equal(await page.locator('[formcontrolname=sample_note]').inputValue(),'Synthetic module specimen note');
   await page.locator('[formcontrolname=status]').selectOption('verified');const verified=page.waitForResponse(r=>r.url().endsWith(`/${module}/worklist/${order.order_id}`)&&r.request().method()==='PUT');await page.getByRole('button',{name:module==='laboratory'?'Save Laboratory Update':'Save Radiology Update',exact:true}).click();assert((await verified).ok());await capture(module+'-result-persistence');
  }
  const stock=await api('GET','/inventory/items?page=1&page_size=10');assert(stock.items.length);const item=stock.items[0];
  const itemCode=await api('POST','/scanner/codes',{record_type:'inventory_item',record_id:item.id,purpose:'stock_label',code_type:'code128'});
  await scan(itemCode.code_value);await page.getByText('Scanned item: '+item.name,{exact:true}).waitFor();await capture('inventory-barcode-exact-item');
  const medicines=await api('GET','/pharmacy/medicines?page=1&page_size=10');assert(medicines.items.length);const medicine=medicines.items[0];
  const medicineCode=await api('POST','/scanner/codes',{record_type:'pharmacy_medicine',record_id:medicine.id,purpose:'product_label',code_type:'code39'});
  await scan(medicineCode.code_value);await page.getByText('Scanned medicine: '+medicine.name,{exact:true}).waitFor();assert.equal(await page.locator('.medicine-editor').getAttribute('open'),null);await capture('medicine-barcode-and-compact-catalog');
  await page.setViewportSize({width:390,height:1050});await capture('mobile-medicine-catalog');const geometry=await page.evaluate(()=>({body:document.querySelector('.page-body').clientWidth,scroll:document.querySelector('.page-body').scrollWidth,document:document.documentElement.scrollWidth}));assert(geometry.scroll<=geometry.body+2&&geometry.document<=390);
  assert.equal(errors.length,0,errors.join('\n'));
 }catch(error){await page.screenshot({path:path.join(output,'failure.png'),fullPage:true});throw error;}
 finally{await fs.writeFile(path.join(output,'report.json'),JSON.stringify({checks,errors},null,2));await browser.close();}
 console.log(`${checks.length} module workflow checks passed`);
})().catch(error=>{console.error(error);process.exitCode=1});
