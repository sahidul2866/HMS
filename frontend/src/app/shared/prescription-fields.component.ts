import { CommonModule } from '@angular/common';
import { Component, Input, Output, EventEmitter } from '@angular/core';
import { FormsModule } from '@angular/forms';

export interface PrescriptionField {
  key: string; label: string; type: string; required?: boolean; visible?: boolean; print_visible?: boolean;
  default?: string | number | boolean | null; options?: string[]; min?: number | null; max?: number | null;
  max_length?: number; column?: string; show_when?: Record<string, unknown> | null;
}
@Component({selector:'app-prescription-fields',standalone:true,imports:[CommonModule,FormsModule],template:`
<div class="clinical-fields">
  @for(field of fields;track field.key){
    @if(visible(field)){
      <section [class.wide]="field.column !== 'left' && field.column !== 'right'">
        <label [attr.for]="'rx-'+field.key">{{field.label}}{{field.required ? ' *' : ''}}</label>
        @switch(field.type){
          @case('section'){<h3>{{field.label}}</h3><hr>}
          @case('columns'){<h4>{{field.label}}</h4>}
          @case('header'){<h3>{{field.label}}</h3>}
          @case('footer'){<p>{{field.default}}</p>}
          @case('checkbox'){<input type="checkbox" [id]="'rx-'+field.key" [ngModel]="values[field.key]" (ngModelChange)="set(field.key,$event)" [disabled]="readonly">}
          @case('radio'){@for(option of field.options;track option){<label><input type="radio" [name]="field.key" [value]="option" [ngModel]="values[field.key]" (ngModelChange)="set(field.key,$event)" [disabled]="readonly">{{option}}</label>}}
          @case('select'){<select [id]="'rx-'+field.key" [ngModel]="values[field.key]" (ngModelChange)="set(field.key,$event)" [disabled]="readonly"><option value="">Select</option>@for(option of field.options;track option){<option [value]="option">{{option}}</option>}</select>}
          @case('number'){<input type="number" [id]="'rx-'+field.key" [min]="field.min ?? null" [max]="field.max ?? null" [ngModel]="values[field.key]" (ngModelChange)="set(field.key,$event)" [disabled]="readonly">}
          @case('date'){<input type="date" [id]="'rx-'+field.key" [ngModel]="values[field.key]" (ngModelChange)="set(field.key,$event)" [disabled]="readonly">}
          @case('medicine'){<input [id]="'rx-'+field.key" [ngModel]="selectedName(field.key)" (ngModelChange)="searchCatalog(field.key,'medicine',$event)" [disabled]="readonly" placeholder="Search approved brand or generic"><select aria-label="Select catalog medicine" (change)="chooseCatalog(field.key,'medicine',$any($event.target).value)" [disabled]="readonly"><option value="">Select and review the intended medicine</option>@for(item of medicines;track item.id){<option [value]="item.id">{{item.name}} {{item.strength}} — {{item.generic_name}}</option>}</select>}
          @case('investigation'){<input [id]="'rx-'+field.key" [ngModel]="selectedName(field.key)" (ngModelChange)="searchCatalog(field.key,'investigation',$event)" [disabled]="readonly" placeholder="Search approved investigations"><select aria-label="Select catalog investigation" (change)="chooseCatalog(field.key,'investigation',$any($event.target).value)" [disabled]="readonly"><option value="">Select an investigation to order</option>@for(item of investigations;track item.id){<option [value]="item.id">{{item.test_name}} — {{item.service_area}}</option>}</select>}
          @case('medicine_rows'){@for(row of medicineRows;track row.id){<div class="repeat-row"><strong>{{row.item_name}}</strong><span>{{row.instructions}} · {{row.quantity}}</span><button type="button" (click)="removeClinicalRow.emit(row)" [disabled]="readonly">Remove medicine</button></div>}<button type="button" (click)="focusClinicalSection.emit('medicine')" [disabled]="readonly">Add or edit medicine</button>}
          @case('investigation_rows'){@for(row of investigationRows;track row.id){<div class="repeat-row"><strong>{{row.item_name}}</strong><button type="button" (click)="removeClinicalRow.emit(row)" [disabled]="readonly">Remove investigation</button></div>}<button type="button" (click)="focusClinicalSection.emit('investigation')" [disabled]="readonly">Add or edit investigation</button>}
          @case('table'){<ng-container *ngTemplateOutlet="rows;context:{$implicit:field}"></ng-container>}
          @case('textarea'){<textarea rows="3" [id]="'rx-'+field.key" [maxlength]="field.max_length || 10000" [ngModel]="values[field.key]" (ngModelChange)="set(field.key,$event)" [disabled]="readonly"></textarea>}
          @case('rich_text'){<textarea rows="4" [id]="'rx-'+field.key" [ngModel]="values[field.key]" (ngModelChange)="set(field.key,$event)" [disabled]="readonly" placeholder="Clinical text; scripts and HTML are not executed"></textarea>}
          @case('notes'){<textarea rows="3" [id]="'rx-'+field.key" [ngModel]="values[field.key]" (ngModelChange)="set(field.key,$event)" [disabled]="readonly"></textarea>}
          @default{<input [id]="'rx-'+field.key" [attr.list]="'options-'+field.key" [maxlength]="field.max_length || 10000" [ngModel]="values[field.key]" (ngModelChange)="set(field.key,$event)" [disabled]="readonly"><datalist [id]="'options-'+field.key">@for(option of field.options;track option){<option [value]="option"></option>}</datalist>}
        }
      </section>
    }
  }
</div>
<ng-template #rows let-field><div *ngFor="let row of rowValues(field.key);let index=index" class="repeat-row"><input aria-label="Entry" [ngModel]="row.name" (ngModelChange)="updateRow(field.key,index,'name',$event)" [disabled]="readonly"><input aria-label="Instructions" [ngModel]="row.instructions" (ngModelChange)="updateRow(field.key,index,'instructions',$event)" [disabled]="readonly"><button type="button" (click)="removeRow(field.key,index)" [disabled]="readonly">Remove</button></div><button type="button" (click)="addRow(field.key)" [disabled]="readonly">Add row</button></ng-template>
`,styles:[`:host{display:block}.clinical-fields{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.wide{grid-column:1/-1}label{display:block;font-weight:600}input:not([type=checkbox]):not([type=radio]),textarea,select{width:100%}.repeat-row{display:flex;gap:6px;margin:6px 0}@media(max-width:760px){.clinical-fields{grid-template-columns:1fr}}`]})
export class PrescriptionFieldsComponent {
  @Input() fields: PrescriptionField[]=[]; @Input() values: Record<string,any>={}; @Input() readonly=false;
  @Input() medicines: any[]=[]; @Input() investigations:any[]=[];
  @Input() medicineRows:any[]=[]; @Input() investigationRows:any[]=[];
  @Output() catalogSearch=new EventEmitter<{kind:string;query:string}>();
  @Output() catalogSelected=new EventEmitter<{kind:string;item:any}>();
  @Output() focusClinicalSection=new EventEmitter<string>();
  @Output() removeClinicalRow=new EventEmitter<any>();
  @Output() valuesChange=new EventEmitter<Record<string,any>>();
  selectedName(key:string):string {const value=this.values[key];return typeof value==='string'?value:value?.name||'';}
  searchCatalog(key:string,kind:string,query:string):void {this.set(key,query);this.catalogSearch.emit({kind,query});}
  chooseCatalog(key:string,kind:string,id:string):void {const item=(kind==='medicine'?this.medicines:this.investigations).find(row=>row.id===id);if(!item)return;this.set(key,{catalog_id:item.id,name:kind==='medicine'?item.name:item.test_name,strength:item.strength,generic:item.generic_name,service_area:item.service_area});this.catalogSelected.emit({kind,item});}
  visible(field:PrescriptionField):boolean{return field.visible!==false && (!field.show_when || Object.entries(field.show_when).every(([key,value])=>this.values[key]===value));}
  set(key:string,value:unknown):void{this.values={...this.values,[key]:value};this.valuesChange.emit(this.values);}
  rowValues(key:string):Array<{name:string;instructions:string}>{return Array.isArray(this.values[key])?this.values[key]:[];}
  addRow(key:string):void{this.set(key,[...this.rowValues(key),{name:'',instructions:''}]);}
  removeRow(key:string,index:number):void{this.set(key,this.rowValues(key).filter((_,i)=>i!==index));}
  updateRow(key:string,index:number,property:string,value:string):void{this.set(key,this.rowValues(key).map((row,i)=>i===index?{...row,[property]:value}:row));}
}
