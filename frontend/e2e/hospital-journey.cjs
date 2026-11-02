/* Local synthetic journey. Run against an already-running development app. */
const fs = require('node:fs/promises');
const path = require('node:path');
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const base = process.env.HMS_E2E_BASE_URL || 'http://127.0.0.1:4200';
const output = process.env.HMS_E2E_ARTIFACTS || '/tmp/hms-erp-journey';
if (!['localhost', '127.0.0.1'].includes(new URL(base).hostname)) throw Error('Synthetic journey requires a local app.');
(async () => {
 await fs.mkdir(output,{recursive:true});
 await Promise.all(['failure.png','failed-request.json'].map(file=>fs.rm(output+'/'+file,{force:true})));
 const browser = await chromium.launch({headless:true,executablePath:process.env.HMS_CHROME_PATH || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 const page = await browser.newPage({viewport:{width:1440,height:1000},timezoneId:'Asia/Dhaka'});
 page.setDefaultTimeout(20000);
 const stages=[], errors=[]; let stage='login'; let token; let apiBase;
 page.on('pageerror',error=>errors.push(error.message));
 page.on('response',r=>{if(r.status()>=400&&r.url().includes('/api/v1/'))errors.push(`${r.status()} ${new URL(r.url()).pathname}`);});
 page.on('response',r=>{if(r.request().method()!=='GET'&&r.url().includes('/api/v1/'))console.log(r.request().method(),new URL(r.url()).pathname,r.status());});
 page.on('dialog',dialog=>dialog.accept(dialog.type()==='prompt'?'Synthetic clinical decision':undefined));
 async function api(method, route, data) {
  const r=await page.request.fetch(apiBase+route,{method,data,headers:{Authorization:'Bearer '+token}});
  assert(r.ok(),`${method} ${route}: ${r.status()} ${await r.text()}`);return r.json();
 }
 async function go(route) {await page.waitForLoadState('load');await page.evaluate(()=>sessionStorage.removeItem('hms.tabs')).catch(async error=>{if(!error.message.includes('Execution context was destroyed'))throw error;await page.waitForLoadState('load');await page.evaluate(()=>sessionStorage.removeItem('hms.tabs'));});await page.goto(base+'/?e2e='+Date.now()+'#'+route,{waitUntil:'networkidle'});await page.locator('app-global-loader .global-loader-card').waitFor({state:'hidden'});}
 async function capture(name) {stages.push({stage:name,passed:true});console.log(name);await page.screenshot({path:path.join(output,name+'.png'),fullPage:true});}
 async function uiPost(route,action,method='POST') {
  const pending=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/v1'+route&&r.request().method()===method);
  const [,r]=await Promise.all([action(),pending]);if(!r.ok())await fs.writeFile(path.join(output,'failed-request.json'),JSON.stringify(r.request().postDataJSON(),null,2));assert(r.ok(),await r.text());return r.json();
 }
 try {
  await page.goto(base,{waitUntil:'networkidle'});
  await page.locator('#login-identity').fill(process.env.HMS_E2E_USER || 'superadmin');
  await page.locator('#login-password').fill(process.env.HMS_E2E_PASSWORD || 'Admin123!');
  await page.getByRole('button',{name:'Sign In',exact:true}).click();await page.waitForURL('**/#/dashboard');
  apiBase=(await (await page.request.get(base+'/assets/app-config.json')).json()).apiBaseUrl || 'http://localhost:8000/api/v1';
  assert(['localhost','127.0.0.1'].includes(new URL(apiBase).hostname),'Synthetic API must be local');
  token=await page.evaluate(()=>localStorage.getItem('hms.accessToken'));
  stage='patient-registration';await go('/patients/new');
  await page.locator('[formcontrolname=first_name]').fill('ERPBrowser');
  await page.locator('[formcontrolname=last_name]').fill('Synthetic'+Date.now());
  await page.locator('[formcontrolname=phone]').fill('017'+String(Date.now()).slice(-8));
  const patient=await uiPost('/patients',()=>page.getByRole('button',{name:'Create Patient',exact:true}).click());
  assert(patient.patient_number);await page.waitForURL('**/#/patients?**');await capture(stage);
  stage='appointment-booking';
  const abandoned=await api('GET','/queue/tokens?queue_scope=opd');
  for(const queued of abandoned){if((queued.patient_label||'').includes(' - ERPBrowser Synthetic')&&['called','recalled','in_progress'].includes(queued.status))await api('POST',`/queue/tokens/${queued.id}/status`,{status:'cancelled',notes:'Close abandoned synthetic browser test token before rerun'});}
  const doctors=await api('GET','/users/doctors?referral_only=true');console.log('Eligible doctors:',doctors.length);let chosen;
  for(let day=1;day<=28&&!chosen;day++){
   const date=new Date();date.setDate(date.getDate()+day);const slotDate=date.toLocaleDateString('en-CA',{timeZone:'Asia/Dhaka'});
   for(const doctor of doctors){const slots=await api('GET',`/appointments/doctor-slots?doctor_user_id=${doctor.id}&slot_date=${slotDate}`);if(slots.slots?.some(s=>s.status==='available')){chosen={doctor,date:slotDate};break;}}
  }
  if(!chosen){
   const date=new Date();date.setDate(date.getDate()+1);const slotDate=date.toLocaleDateString('en-CA',{timeZone:'Asia/Dhaka'});const weekday=(date.getDay()+6)%7;
   for(const doctor of doctors){
    const schedules=await api('GET','/appointments/doctor-schedules?doctor_user_id='+doctor.id);
    if(!schedules.some(s=>s.weekday===weekday)){
     await api('POST','/appointments/doctor-schedules',{doctor_user_id:doctor.id,weekday,start_time:'09:00',end_time:'10:00',slot_duration_minutes:15,buffer_minutes:0});
     chosen={doctor,date:slotDate};break;
    }
   }
  }
  assert(chosen,'No available doctor slots or unused schedule for a synthetic fixture');
  await go('/appointments/create?patientId='+patient.id);
  await page.locator('[formcontrolname=doctor_user_id]').selectOption(chosen.doctor.id);
  await page.locator('[formcontrolname=slot_date]').fill(chosen.date);
  await page.locator('[formcontrolname=reason]').fill('Synthetic ERP browser verification');
  await page.locator('.slot-chip:not([disabled])').first().click();
  const appointment=await uiPost('/appointments',()=>page.getByRole('button',{name:'Create Appointment',exact:true}).click());
  await capture(stage);
  stage='appointment-check-in';await go('/appointments?appointmentId='+appointment.id);
  await page.locator('[formcontrolname=department_name]').fill('Medicine');
  const visit=await uiPost(`/appointments/${appointment.id}/check-in`,()=>page.getByRole('button',{name:'Check In To OPD',exact:true}).click());
  await capture(stage);
  stage='consultation-payment';await go('/billing/create?opdVisitId='+visit.id);
  await page.getByRole('button',{name:'Review payment',exact:true}).click();
  await page.getByRole('button',{name:'Collect full amount',exact:true}).click();
  const paid=page.waitForResponse(r=>r.url().includes('/billing/invoices/')&&r.url().endsWith('/payments')&&r.request().method()==='POST').catch(()=>null);
  const invoice=await uiPost('/billing/invoices',()=>page.getByRole('button',{name:'Post Invoice',exact:true}).click());
  const payment=await paid;assert(payment&&payment.ok(),await payment.text());assert(Number(invoice.total_amount)>0);
  await capture(stage);
  stage='doctor-call';
  // Target only this synthetic token; never call another queued patient during the audit.
  const tokens=await api('GET','/queue/tokens?queue_scope=opd');const queueToken=tokens.find(t=>t.visit_id===visit.id);assert(queueToken);
  await api('POST',`/queue/tokens/${queueToken.id}/status`,{status:'called'});
  await go('/opd/visits?openVisit='+visit.id);await capture(stage);
  stage='prescription';
  await uiPost(`/opd/visits/${visit.id}/status`,()=>page.getByRole('button',{name:'Start Visit',exact:true}).click(),'PUT');
  await page.getByPlaceholder('Final diagnosis',{exact:true}).fill('Synthetic browser verification');
  await page.getByPlaceholder('Medicine name',{exact:true}).fill('Synthetic ERP prescription');
  await page.getByPlaceholder('Qty',{exact:true}).fill('1');
  await uiPost(`/opd/visits/${visit.id}/orders`,()=>page.getByRole('button',{name:'Add Medicine',exact:true}).click());
  await uiPost(`/opd/visits/${visit.id}/finalize`,()=>page.getByRole('button',{name:'Finalize Prescription',exact:true}).click());
  await capture(stage);
  stage='barcode-handoff';
  const scanned=await api('POST','/scanner/resolve',{code:visit.visit_number,expected_record_type:'opd_visit',expected_patient_id:patient.id});
  assert(scanned.success);assert.equal(scanned.records[0].query_params.openVisit,visit.id);
  await go('/patients');
  await page.locator('.topbar app-global-scanner .scan-trigger').click();
  await page.locator('#global-scan-input').fill(visit.visit_number);
  await page.screenshot({path:path.join(output,'barcode-scanner.png')});
  await page.locator('#global-scan-input').press('Enter');
  await page.waitForURL(url=>url.hash.includes('openVisit='+visit.id));
  await page.getByRole('button',{name:'Finalize Prescription',exact:true}).waitFor();
  await capture(stage);
  stage='ipd-admission';
  // Provision one synthetic bed so the journey cannot consume a hospital's existing bed.
  const bed=await api('POST','/ipd/beds',{ward_name:'ERP Browser Test',bed_number:'E2E-'+Date.now(),bed_type:'General',daily_rate:300,status:'available'});
  const admission=await api('POST',`/opd/visits/${visit.id}/convert-to-ipd`,{bed_id:bed.id,admitted_at:new Date().toISOString(),admission_type:'General',ward_name:bed.ward_name,bed_number:bed.bed_number,attending_doctor_name:chosen.doctor.full_name});
  await go('/ipd/admissions/'+admission.id);await capture(stage);
  stage='ipd-care';
  if(process.env.HMS_E2E_IPD_UI==='1'){
   await page.getByRole('button',{name:/^Clinical Work/}).click();
   const doctorForm=page.locator('form').filter({has:page.getByRole('button',{name:'Save Doctor Note',exact:true})});
   await doctorForm.locator('[formcontrolname=note]').fill('Synthetic IPD browser assessment');
   await uiPost(`/ipd/admissions/${admission.id}/clinical-notes`,()=>doctorForm.getByRole('button',{name:'Save Doctor Note',exact:true}).click());
   const nurseForm=page.locator('form').filter({has:page.getByRole('button',{name:'Save Vitals / Nursing Note',exact:true})});
   await nurseForm.locator('[formcontrolname=note]').fill('Synthetic bedside nursing round');
   await nurseForm.locator('[formcontrolname=pulse]').fill('80');
   await uiPost(`/ipd/admissions/${admission.id}/nursing-notes`,()=>nurseForm.getByRole('button',{name:'Save Vitals / Nursing Note',exact:true}).click());
   await api('POST','/billing/services',{service_code:'IPD-MED-'+Date.now(),name:'Synthetic IPD UI medicine',unit_price:20,doctor_share_percentage:0});
   await page.getByRole('button',{name:'Orders',exact:true}).click();
   await page.locator('[formcontrolname=item_name]').fill('Synthetic IPD UI medicine');
   const medOrder=await uiPost(`/ipd/admissions/${admission.id}/orders`,()=>page.getByRole('button',{name:'Create Order',exact:true}).click());
   await page.getByRole('button',{name:'Medication',exact:true}).click();
   await page.getByRole('button',{name:'Record',exact:true}).click();
   await uiPost(`/ipd/admissions/${admission.id}/medications`,()=>page.getByRole('button',{name:'Record Medication',exact:true}).click());
   await page.getByRole('button',{name:'Orders',exact:true}).click();
   await uiPost(`/ipd/admissions/${admission.id}/orders/${medOrder.id}`,()=>page.getByRole('button',{name:'Discontinue',exact:true}).click(),'PATCH');
   await page.setViewportSize({width:390,height:1000});await capture('ipd-mobile-workflow');await page.setViewportSize({width:1440,height:1000});
   await page.getByRole('dialog').getByRole('button',{name:'Close',exact:true}).click();
   const nextBed=await api('POST','/ipd/beds',{ward_name:bed.ward_name,bed_number:'IPD-TRANSFER-'+Date.now(),bed_type:'General',daily_rate:500});
   await go('/ipd/admissions/'+admission.id);
   await page.getByRole('button',{name:/^Transfer/}).click();
   await page.locator('[formcontrolname=bed_id]').selectOption(nextBed.id);
   await page.locator('[formcontrolname=transfer_reason]').fill('Synthetic test transfer');
   await uiPost(`/ipd/admissions/${admission.id}/transfer`,()=>page.getByRole('button',{name:'Transfer Admission',exact:true}).click(),'PUT');
   await page.getByRole('dialog').getByRole('button',{name:'Close',exact:true}).click();
   await go('/ipd/settings');const oldBed=page.locator('.bed-card').filter({hasText:bed.bed_number});
   await oldBed.locator('summary').click();await oldBed.locator('[name=status]').selectOption('available');await oldBed.locator('[name=reason]').fill('Cleaning completed and inspected');
   await uiPost(`/ipd/beds/${bed.id}/status`,()=>oldBed.getByRole('button',{name:'Save bed status',exact:true}).click(),'PATCH');
   await capture('ipd-bed-turnover');
  }else{
  await api('POST',`/ipd/admissions/${admission.id}/clinical-notes`,{note:'Synthetic browser journey assessment',diagnosis:'Synthetic browser verification'});
  await api('POST',`/ipd/admissions/${admission.id}/nursing-notes`,{note:'Synthetic nursing round',pulse:80,spo2:98,systolic_bp:120,diastolic_bp:80});
  }
  await go('/ipd/admissions/'+admission.id);await capture(stage);
  stage='final-billing';await go('/billing/create?ipdAdmissionId='+admission.id+'&billingStage=final');
  await page.getByRole('button',{name:'Review payment',exact:true}).click();
  await page.getByRole('button',{name:'Collect full amount',exact:true}).click();
  const finalPayment=page.waitForResponse(r=>r.url().includes('/billing/invoices/')&&r.url().endsWith('/payments')&&r.request().method()==='POST').catch(()=>null);
  const finalPosted=await uiPost('/billing/invoices',()=>page.getByRole('button',{name:'Post Invoice',exact:true}).click());
  if(process.env.HMS_E2E_IPD_UI==='1')assert.equal(Number(finalPosted.total_amount),520,'Transfer-day bill must use highest bed rate plus the administered medicine');
  assert((await finalPayment).ok());await capture(stage);
  stage='discharge';
  if(process.env.HMS_E2E_IPD_UI==='1'){
   await go('/ipd/admissions/'+admission.id);await page.getByRole('button',{name:/^Discharge/}).click();
   await page.locator('[formcontrolname=discharge_diagnosis]').fill('Synthetic IPD browser diagnosis');
   await page.locator('[formcontrolname=discharge_summary]').fill('Synthetic completed inpatient care journey');
   await uiPost(`/ipd/admissions/${admission.id}/discharge-plan`,()=>page.getByRole('button',{name:'Approve Discharge',exact:true}).click());
   await uiPost(`/ipd/admissions/${admission.id}/discharge`,()=>page.getByRole('button',{name:'Finalize Discharge',exact:true}).click(),'PUT');
   await page.getByRole('button',{name:/^Clinical Work/}).click();
   assert(await page.getByRole('button',{name:'Save Doctor Note',exact:true}).isDisabled(),'Closed admission must prevent new notes');
   await capture('ipd-closed-record');await page.getByRole('dialog').getByRole('button',{name:'Close',exact:true}).click();
  }else{await api('POST',`/ipd/admissions/${admission.id}/discharge-plan?status=approved`);}
  const readiness=await api('GET',`/ipd/admissions/${admission.id}/discharge-readiness`);assert(readiness.blockers.every(b=>b==='Discharge summary'),JSON.stringify(readiness));
  const discharge=process.env.HMS_E2E_IPD_UI==='1'?await api('GET',`/ipd/admissions/${admission.id}`):await api('PUT',`/ipd/admissions/${admission.id}/discharge`,{discharge_condition:'Stable synthetic record',discharge_diagnosis:'Synthetic browser verification',discharge_summary:'Synthetic browser journey completed'});
  assert.equal(discharge.status,'discharged');await go('/ipd/admissions/'+admission.id);await capture(stage);
  stage='billing-operations';await go('/billing/operations');
  await page.getByRole('button',{name:'Types and departments',exact:true}).click();
  await page.locator('[name=code]').fill('E2E_'+Date.now());
  await page.locator('[name=typeName]').fill('Synthetic ERP billing');
  await page.locator('[name=department]').fill('ERP Browser Department');
  const billingType=await uiPost('/billing/types',()=>page.getByRole('button',{name:'Create billing type',exact:true}).click());
  assert.equal(billingType.department,'ERP Browser Department');
  await page.getByRole('button',{name:'Financial reports',exact:true}).click();
  await page.getByRole('button',{name:'Generate saved report',exact:true}).click();
  await page.getByText('By department',{exact:true}).waitFor();await capture(stage);
  stage='invoice-audit';await go('/billing/list?invoiceId='+invoice.id);
  await page.getByRole('button',{name:'Audit history',exact:true}).click();
  await page.getByText('Discount and transaction history',{exact:true}).waitFor();
  await page.getByText('invoice created',{exact:true}).waitFor();await capture(stage);
  assert.equal(errors.length,0,errors.join('\n'));
 } catch(error) {stages.push({stage,passed:false,error:error.message});await page.screenshot({path:path.join(output,'failure.png'),fullPage:true});throw error;}
 finally {await fs.writeFile(path.join(output,'report.json'),JSON.stringify({stages,errors},null,2));await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1});
