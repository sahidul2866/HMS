import { DOCUMENT } from '@angular/common';
import { AfterViewInit, Directive, ElementRef, EventEmitter, HostBinding, HostListener, inject, OnDestroy, Output } from '@angular/core';

let nextDialogId = 0;

/** Accessible focus boundary for an explicitly opened modal. */
@Directive({ selector: '[appDialog]', standalone: true })
export class DialogDirective implements AfterViewInit, OnDestroy {
  private readonly element = inject<ElementRef<HTMLElement>>(ElementRef).nativeElement;
  private readonly document = inject(DOCUMENT);
  private readonly opener = this.document.activeElement as HTMLElement | null;
  private destroyed = false;
  @HostBinding('attr.role') readonly role = 'dialog';
  @HostBinding('attr.aria-modal') readonly modal = 'true';
  @HostBinding('attr.tabindex') readonly tabIndex = '-1';
  @Output() readonly appDialogClose = new EventEmitter<void>();

  ngAfterViewInit(): void {
    const heading = this.element.querySelector<HTMLElement>('h1,h2,h3');
    if (heading) {
      if (!heading.id) heading.id = `app-dialog-title-${++nextDialogId}`;
      this.element.setAttribute('aria-labelledby', heading.id);
    } else {
      this.element.setAttribute('aria-label', 'Dialog');
    }
    queueMicrotask(() => {
      if (!this.destroyed && this.element.isConnected) (this.focusables()[0] || this.element).focus();
    });
  }

  @HostListener('keydown', ['$event'])
  handleKey(event: KeyboardEvent): void {
    if (event.isComposing) return;
    if (event.key === 'Escape') {
      event.preventDefault();event.stopPropagation();this.appDialogClose.emit();
    } else if (event.key === 'Tab') {
      const controls = this.focusables();
      if (!controls.length) { event.preventDefault();this.element.focus();return; }
      const first = controls[0], last = controls[controls.length - 1];
      if (event.shiftKey && (this.document.activeElement === first || this.document.activeElement === this.element)) {
        event.preventDefault();last.focus();
      } else if (!event.shiftKey && (this.document.activeElement === last || this.document.activeElement === this.element)) {
        event.preventDefault();first.focus();
      }
    }
  }

  ngOnDestroy(): void {
    this.destroyed = true;
    if (this.opener?.isConnected) this.opener.focus();
  }

  private focusables(): HTMLElement[] {
    return Array.from(this.element.querySelectorAll<HTMLElement>('button,a[href],input,select,textarea,[tabindex]'))
      .filter(element => element.tabIndex >= 0 && !element.matches(':disabled') && element.checkVisibility());
  }
}
