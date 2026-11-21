import { TestBed } from '@angular/core/testing';
import { PrescriptionFieldsComponent } from '../shared/prescription-fields.component';
import { buildOPDPrescriptionHtml, renderSafeRichText } from '../shared/utils/opd-prescription-printer';
import { OPDVisit } from '../features/opd/models/opd.models';

describe('Configurable prescription fields',()=>{
  it('renders English and Bangla labels and emits independent field changes',()=>{
    const fixture=TestBed.createComponent(PrescriptionFieldsComponent);const component=fixture.componentInstance;
    component.fields=[{key:'allergies',label:'Allergies / অ্যালার্জি',type:'textarea',required:true}];fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('অ্যালার্জি');
    const listener=jasmine.createSpy('field change');component.valuesChange.subscribe(listener);
    component.set('allergies','Recorded allergy');expect(listener).toHaveBeenCalledWith({allergies:'Recorded allergy'});
  });
  it('hides conditional required fields until the configured condition matches',()=>{
    const fixture=TestBed.createComponent(PrescriptionFieldsComponent);const c=fixture.componentInstance;
    const field={key:'gestation',label:'Gestation',type:'number',show_when:{pregnant:true}};
    c.values={pregnant:false};expect(c.visible(field)).toBeFalse();c.values={pregnant:true};expect(c.visible(field)).toBeTrue();
  });
  it('adds, edits and removes repeating rows without changing other clinical data',()=>{
    const c=TestBed.createComponent(PrescriptionFieldsComponent).componentInstance;c.values={allergies:'Retain this history'};
    c.addRow('rows');c.updateRow('rows',0,'name','Explicit entry');expect(c.rowValues('rows')[0].name).toBe('Explicit entry');
    c.removeRow('rows',0);expect(c.rowValues('rows')).toEqual([]);expect(c.values['allergies']).toBe('Retain this history');
  });
  it('uses persisted clinical rows and emits explicit catalog selection without a dose',()=>{
    const fixture=TestBed.createComponent(PrescriptionFieldsComponent);const c=fixture.componentInstance;
    c.fields=[{key:'meds',label:'Medicines',type:'medicine_rows'},{key:'choice',label:'Medicine choice',type:'medicine'}];
    c.medicineRows=[{id:'order',item_name:'Approved test entry',instructions:'Doctor instructions',quantity:1}];
    c.medicines=[{id:'catalog',name:'Approved test entry',strength:'TEST',generic_name:'Verified test generic'}];fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Doctor instructions');
    const selected=jasmine.createSpy('selected');c.catalogSelected.subscribe(selected);
    c.chooseCatalog('choice','medicine','catalog');expect(selected).toHaveBeenCalledWith({kind:'medicine',item:c.medicines[0]});
    expect(c.values['choice'].dose).toBeUndefined();
    const remove=jasmine.createSpy('remove');c.removeClinicalRow.subscribe(remove);
    (fixture.nativeElement.querySelector('button') as HTMLButtonElement).click();expect(remove).toHaveBeenCalledWith(c.medicineRows[0]);
  });
  it('respects editor visibility independently of print visibility',()=>{
    const c=TestBed.createComponent(PrescriptionFieldsComponent).componentInstance;
    expect(c.visible({key:'x',label:'x',type:'text',visible:false,print_visible:true})).toBeFalse();
  });
});

describe('Frozen prescription printing',()=>{
  const base={id:'visit',visit_number:'OPD-TEST',visit_date:'2026-11-19',department_name:'Medicine',consulting_doctor_name:'Dr Current',patient:{first_name:'Current',last_name:'Patient',patient_number:'PAT'},orders:[]} as unknown as OPDVisit;
  it('prints signed clinical and template snapshots instead of later live changes',()=>{
    const visit={...base,prescription_status:'finalized',chief_complaint:'Changed live content',signed_prescription:{chief_complaint:'Original signed complaint',patient:{first_name:'Original',last_name:'Patient',patient_number:'ORIGINAL'},doctor:{opd_prescription_header_name:'Original Doctor',opd_bmdc_registration:'TEST-BMDC'},template_payload:{paper_size:'A4',sections:['complaint'],section_labels:[{key:'complaint',label:'Original label',placement:'full',height:40}]},orders:[],signed_at:'2026-11-19T10:00:00Z'}};
    const html=buildOPDPrescriptionHtml({visit});expect(html).toContain('Original signed complaint');expect(html).not.toContain('Changed live content');
    expect(html).toContain('Original Doctor');expect(html).toContain('TEST-BMDC');expect(html).toContain('size: A4');expect(html).toContain('Original label');
  });
  it('does not put an old signature on an amended unsigned draft',()=>{
    const html=buildOPDPrescriptionHtml({visit:{...base,prescription_status:'amended',signed_prescription:{signed_at:'OLD',doctor:{opd_signature_image:'data:image/png;base64,AAAA'}}}});
    expect(html).toContain('DRAFT — NOT SIGNED');expect(html).not.toContain('Signed electronically: OLD');expect(html).not.toContain('alt="Doctor signature"');
  });
  it('keeps hidden custom fields out of print while preserving safe rich text and Unicode',()=>{
    const html=buildOPDPrescriptionHtml({visit:{...base,prescription_data:{private:'Private editor value',advice:'**বাংলা** _advice_ <script>unsafe()</script>'}},layoutProfile:{payload:{fields:[{key:'private',label:'Private',print_visible:false},{key:'advice',label:'Advice',type:'rich_text'}]}} as any});
    expect(html).not.toContain('Private editor value');expect(html).toContain('<strong>বাংলা</strong>');expect(html).not.toContain('<script>unsafe()');expect(html).toContain('&lt;script&gt;');
  });
  it('limits paper size configuration to safe built-in values or validated dimensions',()=>{
    const html=buildOPDPrescriptionHtml({visit:base,layoutProfile:{payload:{paper_size:'custom',paper_width_mm:160,paper_height_mm:230,margin_mm:10}} as any});
    expect(html).toContain('size: 160mm 230mm; margin: 10mm');
  });
  it('marks voided prescriptions visibly and keeps their original content',()=>{
    const html=buildOPDPrescriptionHtml({visit:{...base,prescription_status:'voided',signed_prescription:{void_reason:'Wrong encounter',orders:[],patient:base.patient,doctor:{},template_payload:{}}}});
    expect(html).toContain('VOIDED / ENTERED IN ERROR — Wrong encounter');
  });
  it('escapes HTML before applying restricted rich-text marks',()=>{
    expect(renderSafeRichText('**<img onerror=bad>**')).toBe('<strong>&lt;img onerror=bad&gt;</strong>');
  });
});
