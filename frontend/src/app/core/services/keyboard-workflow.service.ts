import { DOCUMENT } from '@angular/common';
import { Injectable, NgZone, inject } from '@angular/core';

import { NotificationService } from './notification.service';

@Injectable({ providedIn: 'root' })
export class KeyboardWorkflowService {
  private readonly document = inject(DOCUMENT);
  private readonly zone = inject(NgZone);
  private readonly notifications = inject(NotificationService);
  private started = false;
  private pendingSubmit = new WeakSet<HTMLFormElement>();
  private observer?: MutationObserver;

  start(): void {
    if (this.started) return;
    this.started = true;
    this.zone.runOutsideAngular(() => {
      this.document.addEventListener('keydown', this.handleKeydown, true);
      this.document.addEventListener('submit', this.handleSubmit, true);
      this.enhanceKeyboardTargets();
      this.observer = new MutationObserver(() => this.enhanceKeyboardTargets());
      this.observer.observe(this.document.body, { childList: true, subtree: true });
    });
  }

  private readonly handleSubmit = (event: Event): void => {
    const form = event.target instanceof HTMLFormElement ? event.target : null;
    if (!form) return;
    if (this.pendingSubmit.has(form)) {
      event.preventDefault();
      event.stopImmediatePropagation();
      this.zone.run(() => this.notifications.warning('Submission already in progress'));
      return;
    }
    this.pendingSubmit.add(form);
    form.classList.add('app-submitting');
    window.setTimeout(() => {
      this.pendingSubmit.delete(form);
      form.classList.remove('app-submitting');
    }, 1800);
  };

  private readonly handleKeydown = (event: KeyboardEvent): void => {
    const target = event.target instanceof HTMLElement ? event.target : null;
    if (!target) return;

    if (event.key === 'Escape') {
      if (this.closeTransientUi(target)) {
        event.preventDefault();
      }
      return;
    }

    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
      if (this.clickAction('[data-shortcut="save"], [data-action="save"], button[type="submit"]')) {
        event.preventDefault();
      }
      return;
    }

    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'p') {
      if (this.clickAction('[data-shortcut="print"], [data-action="print"], .print-btn')) {
        event.preventDefault();
      }
      return;
    }

    if (event.key === 'Enter' && !event.shiftKey && this.shouldAdvanceOnEnter(target)) {
      const form = target.closest('form');
      if (form && this.isLastFormControl(form, target)) {
        event.preventDefault();
        this.submitFormSafely(form);
      } else if (form) {
        event.preventDefault();
        this.focusNextControl(form, target);
      }
      return;
    }

    if (event.key === 'Enter' && target.matches('[data-enter-click], .keyboard-row-action')) {
      event.preventDefault();
      target.click();
      return;
    }

    if ((event.key === 'ArrowDown' || event.key === 'ArrowUp') && target.closest('table')) {
      if (this.moveTableFocus(target, event.key === 'ArrowDown' ? 1 : -1)) {
        event.preventDefault();
      }
    }
  };

  private enhanceKeyboardTargets(): void {
    const rows = Array.from(this.document.querySelectorAll<HTMLTableRowElement>('tbody tr:not([tabindex])'));
    rows.forEach((row) => {
      row.tabIndex = 0;
      row.classList.add('keyboard-row-action');
    });
    const unsafe = Array.from(this.document.querySelectorAll<HTMLButtonElement>('button'));
    unsafe.forEach((button) => {
      const label = `${button.textContent || ''} ${button.getAttribute('aria-label') || ''}`.toLowerCase();
      if (/(delete|cancel|refund|discharge|approve|discard|void|reset|clear|override|release)/.test(label)) {
        button.dataset['dangerAction'] = 'true';
      }
    });
  }

  private shouldAdvanceOnEnter(target: HTMLElement): boolean {
    if (target instanceof HTMLTextAreaElement || target instanceof HTMLButtonElement) return false;
    if (target instanceof HTMLInputElement && ['button', 'submit', 'checkbox', 'radio', 'file'].includes(target.type)) return false;
    return target instanceof HTMLInputElement || target instanceof HTMLSelectElement;
  }

  private isLastFormControl(form: HTMLFormElement, target: HTMLElement): boolean {
    const controls = this.formControls(form);
    return controls.indexOf(target) === controls.length - 1;
  }

  private focusNextControl(form: HTMLFormElement, target: HTMLElement): void {
    const controls = this.formControls(form);
    const next = controls[controls.indexOf(target) + 1];
    next?.focus();
  }

  private formControls(form: HTMLFormElement): HTMLElement[] {
    return Array.from(form.querySelectorAll<HTMLElement>('input, select, textarea, button[type="submit"]')).filter((item) => {
      if (item.hasAttribute('disabled')) return false;
      if (item instanceof HTMLInputElement && item.type === 'hidden') return false;
      return item.offsetParent !== null;
    });
  }

  private submitFormSafely(form: HTMLFormElement): void {
    const submit = form.querySelector<HTMLButtonElement>('button[type="submit"]:not([disabled])');
    if (!submit) return;
    if (submit.dataset['dangerAction'] === 'true') {
      this.zone.run(() => this.notifications.warning('Use the button confirmation for this action'));
      return;
    }
    submit.click();
  }

  private clickAction(selector: string): boolean {
    const button = this.document.querySelector<HTMLButtonElement>(`${selector}:not([disabled])`);
    if (!button || button.dataset['dangerAction'] === 'true') return false;
    button.click();
    return true;
  }

  private closeTransientUi(target: HTMLElement): boolean {
    const dialogClose = this.document.querySelector<HTMLButtonElement>('[aria-label="Close"], .modal-close, .ghost');
    if (dialogClose && target.closest('[role="dialog"], .scan-backdrop, .command-backdrop')) {
      dialogClose.click();
      return true;
    }
    const active = this.document.activeElement instanceof HTMLElement ? this.document.activeElement : null;
    active?.blur();
    return !!active;
  }

  private moveTableFocus(target: HTMLElement, direction: 1 | -1): boolean {
    const table = target.closest('table');
    const row = target.closest('tr');
    if (!table || !row) return false;
    const rows = Array.from(table.querySelectorAll<HTMLTableRowElement>('tbody tr'));
    const index = rows.indexOf(row);
    const next = rows[index + direction];
    if (!next) return false;
    next.focus();
    next.scrollIntoView({ block: 'nearest' });
    return true;
  }
}

