import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { TestBed, fakeAsync, flushMicrotasks } from '@angular/core/testing';
import { DialogDirective } from '../shared/directives/dialog.directive';

@Component({standalone:true,imports:[CommonModule,DialogDirective],template:`
  <button id="opener" (click)="open=true">Open editor</button>
  <section *ngIf="open" appDialog (appDialogClose)="open=false"><h2>Review patient</h2><button id="first" (click)="open=false">Close</button><input disabled><input id="last" aria-label="Note"></section>
`})
class DialogHost { open=false; }

describe('modal keyboard navigation',()=>{
 it('focuses the dialog, wraps Tab in both directions and restores the opener on Escape',fakeAsync(()=>{
  TestBed.configureTestingModule({imports:[DialogHost]});const fixture=TestBed.createComponent(DialogHost);fixture.detectChanges();
  const opener=fixture.nativeElement.querySelector('#opener') as HTMLButtonElement;opener.focus();opener.click();fixture.detectChanges();flushMicrotasks();
  const dialog=fixture.nativeElement.querySelector('[role=dialog]') as HTMLElement;
  const first=dialog.querySelector('#first') as HTMLElement,last=dialog.querySelector('#last') as HTMLElement;
  expect(document.activeElement).toBe(first);
  expect(dialog.getAttribute('aria-modal')).toBe('true');expect(document.getElementById(dialog.getAttribute('aria-labelledby')!)?.textContent).toBe('Review patient');
  first.dispatchEvent(new KeyboardEvent('keydown',{key:'Tab',shiftKey:true,bubbles:true,cancelable:true}));expect(document.activeElement).toBe(last);
  last.dispatchEvent(new KeyboardEvent('keydown',{key:'Tab',bubbles:true,cancelable:true}));expect(document.activeElement).toBe(first);
  first.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true,cancelable:true}));fixture.detectChanges();expect(fixture.componentInstance.open).toBeFalse();expect(document.activeElement).toBe(opener);
 }));
});
