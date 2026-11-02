/* Read-only expanded form review: open and close dialogs; never press save. */
const fs=require('node:fs/promises');
const path=require('node:path');
const {chromium}=require('playwright');
const base=process.env.HMS_E2E_BASE_URL||'http://127.0.0.1:4200';
const output=process.env.HMS_E2E_ARTIFACTS||'/tmp/hms-module-dialogs';
if(!['localhost','127.0.0.1'].includes(new URL(base).hostname))throw Error('Local app required');
const flows=[['/ot','Book OT','.modal-card'],['/ot','Rooms','.modal-card'],['/ot/checklist','Pre-Op','.modal-card'],['/hr','Add Employee','.modal-card'],['/hr','Run Payroll','.modal-card'],['/transport/vehicles','Add Vehicle','.modal-card'],['/catering/diet-orders','Add order','.catering-dialog']];
(async()=>{
 await fs.mkdir(output,{recursive:true});const browser=await chromium.launch({headless:true,executablePath:process.env.HMS_CHROME_PATH||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});const page=await browser.newPage({viewport:{width:1440,height:1050}});page.setDefaultTimeout(12000);
 const checks=[],errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('response',r=>{if(r.status()>=400&&r.url().includes('/api/v1/'))errors.push(`${r.status()} ${new URL(r.url()).pathname}`);});
 try{
  await page.goto(base,{waitUntil:'networkidle'});await page.locator('#login-identity').fill(process.env.HMS_E2E_USER||'superadmin');await page.locator('#login-password').fill(process.env.HMS_E2E_PASSWORD||'Admin123!');await page.getByRole('button',{name:'Sign In',exact:true}).click();await page.waitForURL('**/#/dashboard');
  for(const width of [1440,1024,768,390])for(const [route,action,selector] of flows){
   const check={width,route,action};
   try{
    await page.setViewportSize({width,height:1050});await page.evaluate(()=>sessionStorage.removeItem('hms.tabs'));await page.goto(base+'/?dialogs='+Date.now()+'#'+route,{waitUntil:'networkidle'});
    await page.getByRole('button',{name:action,exact:true}).first().click();const modal=page.locator(selector).filter({visible:true}).last();await modal.waitFor();
    Object.assign(check,await modal.evaluate(el=>{const r=el.getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,modalWidth:r.width,clientWidth:el.clientWidth,scrollWidth:el.scrollWidth,role:el.getAttribute('role'),fields:el.querySelectorAll('input,select,textarea').length};}));
    check.flags=[check.left<0||check.right>width+1?'outside-viewport':null,check.scrollWidth>check.clientWidth+2?'inner-overflow':null,!check.role?'missing-dialog-role':null].filter(Boolean);
    await page.screenshot({path:path.join(output,width+'_'+route.slice(1).replaceAll('/','_')+'_'+action.replaceAll(' ','-')+'.png'),fullPage:true});
    await modal.getByRole('button',{name:/^(Close|Close dialog|x)$/}).first().click();await modal.waitFor({state:'hidden'});
   }catch(error){check.error=error.message;}
   checks.push(check);await fs.writeFile(path.join(output,'report.json'),JSON.stringify({checks,errors},null,2));if(check.flags?.length||check.error)console.log(JSON.stringify(check));
  }
 }finally{await fs.writeFile(path.join(output,'report.json'),JSON.stringify({checks,errors},null,2));await browser.close();}
 console.log(`${checks.length} expanded dialog checks; ${checks.filter(c=>c.error||c.flags?.length).length} need review`);if(errors.length||checks.some(c=>c.error))process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1});
