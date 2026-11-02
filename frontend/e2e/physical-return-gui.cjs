const fs=require('node:fs/promises');const assert=require('node:assert/strict');const {chromium}=require('playwright');
(async()=>{
 const tokens=JSON.parse(await fs.readFile('/tmp/hms-role-tokens.json','utf8'));const flow=JSON.parse(await fs.readFile('/tmp/hms-physical-return-roleflow.json','utf8'));const base=process.env.HMS_E2E_BASE_URL||'http://127.0.0.1:4200';assert(['localhost','127.0.0.1'].includes(new URL(base).hostname));
 const browser=await chromium.launch({headless:true,executablePath:process.env.HMS_CHROME_PATH||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=400&&r.url().includes('/api/v1/'))errors.push(r.status()+' '+new URL(r.url()).pathname);});
 await page.addInitScript(token=>localStorage.setItem('hms.accessToken',token),tokens.Pharmacist.token);
 try{for(const width of [1440,390]){
 await page.setViewportSize({width,height:1050});await page.goto(base+'/?returnGUI='+Date.now()+'#/pharmacy/dispense/workbench?dispenseId='+flow.dispense_id,{waitUntil:'networkidle'});
 const form=page.locator('form').filter({has:page.locator('[formcontrolname=inspected]')});await form.waitFor();await form.locator('[formcontrolname=source_issue_id]').selectOption({index:1});await form.locator('[formcontrolname=quantity]').fill('1');await form.locator('[formcontrolname=note]').fill('Read-only inspection of physical return controls');await form.locator('[formcontrolname=inspected]').check();
 assert.equal(await form.locator('.smart-suggestion-strip').count(),0,'Return inspection must not show unrelated clinical suggestions');
 assert(!await form.locator('[formcontrolname=restock]').isChecked(),'Disposal must remain the safe default');
 await form.scrollIntoViewIfNeeded();await page.screenshot({path:`/tmp/hms-physical-return-${width}.png`,fullPage:true});const bounds=await page.locator('.page-body').evaluate(el=>({width:el.clientWidth,scroll:el.scrollWidth}));assert(bounds.scroll<=bounds.width+2,'Return workspace overflows');
 }
 assert.equal(errors.length,0,errors.join('\n'));console.log('Pharmacist return GUI passed at 1440 and 390px; forms were not posted');
 }catch(error){await page.screenshot({path:'/tmp/hms-physical-return-failure.png',fullPage:true});console.error(JSON.stringify({url:page.url(),errors,body:(await page.locator('body').innerText()).slice(-4500)}));throw error;}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
