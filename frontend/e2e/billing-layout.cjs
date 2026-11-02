/* Read-only visual review: edits local forms but never posts an invoice/payment. */
const fs=require('node:fs/promises');
const assert=require('node:assert/strict');
const {chromium}=require('playwright');
const base=process.env.HMS_E2E_BASE_URL||'http://127.0.0.1:4200';
const output=process.env.HMS_E2E_ARTIFACTS||'/tmp/hms-billing-layout';
assert(['localhost','127.0.0.1'].includes(new URL(base).hostname));
(async()=>{
 await fs.mkdir(output,{recursive:true});
 await Promise.all(['failure.png','failed-request.json'].map(file=>fs.rm(output+'/'+file,{force:true})));
 const browser=await chromium.launch({headless:true,executablePath:process.env.HMS_CHROME_PATH||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 const page=await browser.newPage({viewport:{width:1440,height:1050}});page.setDefaultTimeout(20000);
 const checks=[],errors=[];page.on('dialog',dialog=>dialog.accept());
 page.on('pageerror',e=>errors.push(e.message));
 page.on('response',r=>{if(r.status()>=400&&r.url().includes('/api/v1/'))errors.push(`${r.status()} ${new URL(r.url()).pathname}`);});
 async function go(route){await page.evaluate(()=>sessionStorage.removeItem('hms.tabs'));await page.goto(base+'/?layout='+Date.now()+'#'+route,{waitUntil:'networkidle'});}
 async function capture(name){await page.screenshot({path:output+'/'+name+'.png',fullPage:true});}
 try{
  await page.goto(base,{waitUntil:'networkidle'});
  await page.locator('#login-identity').fill(process.env.HMS_E2E_USER||'superadmin');await page.locator('#login-password').fill(process.env.HMS_E2E_PASSWORD||'Admin123!');
  await page.getByRole('button',{name:'Sign In',exact:true}).click();await page.waitForURL('**/#/dashboard');
  const token=await page.evaluate(()=>localStorage.getItem('hms.accessToken'));
  const cfg=await(await page.request.get(base+'/assets/app-config.json')).json();
  assert(['localhost','127.0.0.1'].includes(new URL(cfg.apiBaseUrl).hostname));
  const patients=await(await page.request.get(cfg.apiBaseUrl+'/patients',{headers:{Authorization:'Bearer '+token}})).json();assert(patients.length);
  for(const width of [1440,1024,768,390]){
   await page.setViewportSize({width,height:1050});await go('/billing/create?patientId='+patients[0].id);
   await page.getByRole('heading',{name:'Services and items',exact:true}).waitFor();
   await page.getByText('Browse suggested services',{exact:true}).click();
   for(let i=0;i<3;i++)await page.locator('.quick-add-btn').first().click();
   await page.getByText('Browse suggested services',{exact:true}).click();
   await page.locator('.invoice-items-panel').scrollIntoViewIfNeeded();
   const metrics=await page.locator('.invoice-row').evaluateAll(rows=>rows.map(row=>{const rect=row.getBoundingClientRect();return {width:rect.width,height:rect.height,right:rect.right,columns:getComputedStyle(row).gridTemplateColumns,children:[...row.children].map(el=>{const r=el.getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom};})};}));
   assert(metrics.length>=3);for(const row of metrics){assert(row.right<=width+1,'Item row exceeds viewport');assert(row.height<230,'Item row collapsed into a tall stack');for(let a=0;a<row.children.length;a++)for(let b=a+1;b<row.children.length;b++){const x=row.children[a],y=row.children[b];assert(!(Math.min(x.right,y.right)-Math.max(x.left,y.left)>2&&Math.min(x.bottom,y.bottom)-Math.max(x.top,y.top)>2),'Item controls overlap');}}
   assert.equal(await page.getByRole('button',{name:'Post Invoice',exact:true}).count(),0,'Posting is hidden until review');
   await capture(width+'-items');
   const quantity=await page.getByRole('spinbutton',{name:'Item quantity',exact:true}).first().inputValue();
   await page.getByRole('button',{name:'Review payment',exact:true}).click();
   await page.getByRole('heading',{name:'Review and payment',exact:true}).waitFor();assert.equal(await page.locator('.invoice-row').count(),0,'Item editing stays on its own step');await capture(width+'-payment');
   await page.getByRole('button',{name:'Edit items',exact:true}).click();assert.equal(await page.getByRole('spinbutton',{name:'Item quantity',exact:true}).first().inputValue(),quantity,'Back navigation preserves the draft');
   checks.push({width,stage:'billing items/payment',rows:metrics});
   for(const route of ['/opd/visits','/billing/list']){await go(route);await page.locator('h1').waitFor();await capture(width+route.replaceAll('/','-'));const layout=await page.evaluate(()=>({width:document.documentElement.scrollWidth,viewport:innerWidth}));assert(layout.width<=layout.viewport+1,'List causes document overflow');checks.push({width,route,...layout});if(route==='/billing/list'){await page.getByRole('button',{name:'Open',exact:true}).first().click();await page.getByRole('button',{name:'Overview',exact:true}).waitFor();await capture(width+'-invoice-detail');await page.getByRole('button',{name:'Payments and returns',exact:true}).click();await page.locator('summary').filter({hasText:/^Collect Payment$/}).waitFor();await page.getByRole('button',{name:'Audit history',exact:true}).click();await page.getByText('Discount and transaction history',{exact:true}).waitFor();await page.getByRole('dialog').getByRole('button',{name:'Close',exact:true}).click();}}
   await go('/billing/operations');
   if(width<=1100) {
    assert(await page.locator('.topbar').evaluate(el=>el.getBoundingClientRect().height)<90,'Mobile header leaves room for the workflow');
    assert.equal(await page.getByRole('group',{name:'Page space',exact:true}).count(),0,'Display preferences stay in the account menu');
    await page.getByRole('button',{name:'Open account menu',exact:true}).click();
    await page.getByRole('group',{name:'Page space',exact:true}).waitFor();
    await page.getByRole('button',{name:'Open user manual',exact:true}).waitFor();
    await page.getByRole('button',{name:'Open account menu',exact:true}).click();
   }

   for(const name of ['Types and departments','Cash handover','Financial reports']) {
    await page.getByRole('button',{name,exact:true}).click();
    await capture(width+'-operations-'+name.toLowerCase().replaceAll(' ','-'));
    const geometry=await page.evaluate(()=>({width:document.documentElement.scrollWidth,viewport:innerWidth,content:document.querySelector('.page-body').clientWidth,scroll:document.querySelector('.page-body').scrollWidth}));
    assert(geometry.width<=geometry.viewport+1 && geometry.scroll<=geometry.content+2,'Operations view overflows');
   }
   assert.equal(await page.locator('[name=code]').count(),0,'Setup fields stay on their own view');
   const launcher=page.getByRole('button',{name:'Hospital assistant',exact:true});
   assert.notEqual(await launcher.evaluate(el=>getComputedStyle(el.closest('app-floating-assistant')).position),'fixed','Assistant launcher stays out of the work area');
   await launcher.click();await page.getByRole('button',{name:'Close assistant',exact:true}).click();
   checks.push({width,stage:'operations views and assistant'});
  }
  assert.equal(errors.length,0,errors.join('\n'));
 }catch(e){await capture('failure');throw e;}
 finally{await fs.writeFile(output+'/report.json',JSON.stringify({checks,errors},null,2));await browser.close();}
 console.log(`${checks.length} layout checks passed`);
})().catch(e=>{console.error(e);process.exitCode=1});
