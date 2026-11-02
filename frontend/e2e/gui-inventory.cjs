/* Read-only inventory of every static menu page. Flags require screenshot review. */
const fs=require('node:fs/promises');
const path=require('node:path');
const {chromium}=require('playwright');
const base=process.env.HMS_E2E_BASE_URL||'http://127.0.0.1:4200';
const output=process.env.HMS_E2E_ARTIFACTS||'/tmp/hms-gui-inventory';
if(!['127.0.0.1','localhost'].includes(new URL(base).hostname))throw Error('Use a local app for the GUI inventory.');
(async()=>{
 const source=await fs.readFile(path.join(__dirname,'../src/app/navigation/menu.config.ts'),'utf8');
 let routes=[...new Set([...source.matchAll(/route:\s*'([^']+)'/g)].map(m=>m[1]).concat(['/billing/operations']))];
 if(process.env.HMS_GUI_ROUTES)routes=routes.filter(route=>process.env.HMS_GUI_ROUTES.split(',').includes(route));
 if(!routes.length)throw Error('No matching static routes selected');
 const widths=(process.env.HMS_GUI_WIDTHS||'1440,390').split(',').map(Number);
 await fs.mkdir(output,{recursive:true});
 const browser=await chromium.launch({headless:true,executablePath:process.env.HMS_CHROME_PATH||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 const page=await browser.newPage({viewport:{width:1440,height:1050}});page.setDefaultTimeout(12000);
 const pages=[],errors=[];let route='login';
 page.on('pageerror',e=>errors.push({route,type:'javascript',message:e.message}));
 page.on('response',r=>{if(r.status()>=400&&r.url().includes('/api/v1/'))errors.push({route,type:'api',status:r.status(),path:new URL(r.url()).pathname});});
 page.on('dialog',d=>d.accept());
 try{
  await page.goto(base,{waitUntil:'networkidle'});await page.locator('#login-identity').fill(process.env.HMS_E2E_USER||'superadmin');await page.locator('#login-password').fill(process.env.HMS_E2E_PASSWORD||'Admin123!');await page.getByRole('button',{name:'Sign In',exact:true}).click();await page.waitForURL('**/#/dashboard');
  for(const width of widths){await page.setViewportSize({width,height:1050});for(const target of routes){route=target;const before=errors.length;let result={route,width};
   try{
    await page.evaluate(()=>sessionStorage.removeItem('hms.tabs'));
    await page.goto(base+'/?gui='+Date.now()+'#'+route,{waitUntil:'domcontentloaded'});
    await page.locator('.page-body').waitFor();await page.waitForLoadState('networkidle',{timeout:10000}).catch(()=>{});
    result={...result,...await page.evaluate(()=>{const body=document.querySelector('.page-body');const visible=el=>el.checkVisibility()&&el.getBoundingClientRect().width>0;const fields=[...body.querySelectorAll('input:not([type=hidden]),select,textarea')].filter(visible);const cards=[...body.querySelectorAll('.page-card,.soft-panel')].filter(visible);return {url:location.hash,heading:body.querySelector('h1')?.textContent?.trim(),contentWidth:body.clientWidth,contentScroll:body.scrollWidth,documentWidth:document.documentElement.scrollWidth,visibleFields:fields.length,visibleCards:cards.length,aboveFoldFields:fields.filter(el=>{const r=el.getBoundingClientRect();return r.top<innerHeight&&r.bottom>0}).length,wideElements:[...body.querySelectorAll('section,form,table')].filter(el=>visible(el)&&el.getBoundingClientRect().width>body.clientWidth+2&&!el.closest('.table-wrap,.table-shell,.responsive-table')).slice(0,6).map(el=>({tag:el.tagName,class:el.className,width:Math.round(el.getBoundingClientRect().width)}))};})};
    result.flags=[!result.heading?'no-h1':null,result.contentScroll>result.contentWidth+2?'content-overflow':null,result.aboveFoldFields>18?'dense-first-screen':null,result.visibleFields>45?'large-form':null].filter(Boolean);
    await page.screenshot({path:path.join(output,width+'_'+route.slice(1).replaceAll('/','_')+'.png'),fullPage:true});
   }catch(e){result.error=e.message;}
   result.apiErrors=errors.slice(before);pages.push(result);
   await fs.writeFile(path.join(output,'report.json'),JSON.stringify({pages,errors},null,2));
   if(result.flags?.length||result.error||result.apiErrors.length)console.log(JSON.stringify(result));
   else if(pages.length%10===0)console.log(`Reviewed ${pages.length}/${routes.length*widths.length}`);
  }}
 }finally{await fs.writeFile(path.join(output,'report.json'),JSON.stringify({pages,errors},null,2));await browser.close();}
 console.log(`Reviewed ${pages.length} route/viewport pairs; ${pages.filter(p=>p.flags?.length||p.error||p.apiErrors.length).length} need inspection`);
 if(errors.length || pages.some(p=>p.error)) process.exitCode=1;
})().catch(e=>{console.error(e);process.exitCode=1});
