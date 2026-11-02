import { DOCUMENT } from '@angular/common';
import { inject, Injectable, NgZone, OnDestroy } from '@angular/core';

import { NotificationService } from './notification.service';

@Injectable({ providedIn: 'root' })
export class GlobalFormValidationService implements OnDestroy {
  private readonly document = inject(DOCUMENT);
  private readonly zone = inject(NgZone);
  private readonly notificationService = inject(NotificationService);
  private started = false;
  private observer: MutationObserver | null = null;

  start(): void {
    if (this.started) return;
    this.started = true;
    this.zone.runOutsideAngular(() => {
      this.document.addEventListener('submit', this.handleSubmit, true);
      this.document.addEventListener('input', this.handleControlChange, true);
      this.document.addEventListener('change', this.handleControlChange, true);
      this.enhanceSearchableSelects();
      this.observer = new MutationObserver(() => this.enhanceSearchableSelects());
      this.observer.observe(this.document.body, { childList: true, subtree: true });
    });
  }

  ngOnDestroy(): void {
    this.observer?.disconnect();
    this.document.removeEventListener('submit', this.handleSubmit, true);
    this.document.removeEventListener('input', this.handleControlChange, true);
    this.document.removeEventListener('change', this.handleControlChange, true);
  }

  private readonly handleSubmit = (event: Event): void => {
    const form = event.target instanceof HTMLFormElement ? event.target : null;
    if (!form) return;
    if (form.hasAttribute('data-skip-global-validation')) return;
    if (!this.isInvalidForm(form)) {
      form.classList.remove('app-form-submitted');
      form.querySelector('.app-validation-summary')?.remove();
      return;
    }
    event.preventDefault();
    event.stopImmediatePropagation();
    this.renderValidation(form);
  };

  private readonly handleControlChange = (event: Event): void => {
    const target = event.target instanceof Element ? event.target : null;
    const form = target?.closest('form');
    if (!form || !form.classList.contains('app-form-submitted')) return;
    // Angular updates control validity later in the same input event.
    queueMicrotask(() => this.updateValidation(form));
  };

  private updateValidation(form: HTMLFormElement): void {
    this.renderFieldErrors(form);
    const summary = form.querySelector<HTMLElement>('.app-validation-summary');
    if (!summary) return;
    const missingFields = this.invalidFieldLabels(form);
    if (missingFields.length) {
      summary.innerHTML = `<strong>Fix before saving:</strong><span>${this.escapeHtml(missingFields.join(', '))}</span>`;
      return;
    }
    form.classList.remove('app-form-submitted');
    summary.remove();
  }

  private isInvalidForm(form: HTMLFormElement): boolean {
    return form.classList.contains('ng-invalid') || !form.checkValidity();
  }

  private renderValidation(form: HTMLFormElement): void {
    form.classList.add('app-form-submitted');
    this.renderFieldErrors(form);
    const missingFields = this.invalidFieldLabels(form);
    if (!missingFields.length) return;

    let summary = form.querySelector<HTMLElement>('.app-validation-summary');
    if (!summary) {
      summary = this.document.createElement('div');
      summary.className = 'app-validation-summary';
      summary.setAttribute('role', 'alert');
      form.prepend(summary);
    }
    summary.innerHTML = `<strong>Fix before saving:</strong><span>${this.escapeHtml(missingFields.join(', '))}</span>`;
    const first = form.querySelector<HTMLElement>('[aria-invalid="true"]');
    let ancestor = first?.parentElement;
    while (ancestor) {
      if (ancestor instanceof HTMLDetailsElement) ancestor.open = true;
      ancestor = ancestor.parentElement;
    }
    first?.focus();
    summary.scrollIntoView({ block: 'center', behavior: 'smooth' });

    this.zone.run(() => {
      this.notificationService.error(`Fix before saving: ${missingFields.join(', ')}`);
    });
  }

  private fieldErrorId = 0;

  private renderFieldErrors(form: HTMLFormElement): void {
    for (const control of Array.from(form.querySelectorAll<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>('input, select, textarea'))) {
      const previousId = control.dataset['appErrorId'];
      if (previousId) {
        this.document.getElementById(previousId)?.remove();
        const descriptions = (control.getAttribute('aria-describedby') || '').split(' ').filter(id => id && id !== previousId);
        if (descriptions.length) control.setAttribute('aria-describedby', descriptions.join(' '));
        else control.removeAttribute('aria-describedby');
        control.removeAttribute('aria-invalid');
        delete control.dataset['appErrorId'];
      }
      if (!this.isInvalidControl(control)) continue;
      const error = this.document.createElement('span');
      error.id = `app-field-error-${++this.fieldErrorId}`;
      error.className = 'app-field-error';
      const validity = control.validity;
      const hint = validity.valueMissing ? 'Enter a value for this field.'
        : validity.typeMismatch ? 'Enter a valid ' + (control instanceof HTMLInputElement && control.type === 'email' ? 'email address.' : 'value.')
        : validity.rangeUnderflow ? `Enter a value of at least ${control.getAttribute('min')}.`
        : validity.rangeOverflow ? `Enter a value no greater than ${control.getAttribute('max')}.`
        : validity.tooShort ? `Use at least ${control.getAttribute('minlength')} characters.`
        : validity.patternMismatch ? (control.getAttribute('title') || 'Use the requested format.')
        : validity.stepMismatch ? 'Enter a value matching the allowed increment.'
        : 'Check this value against the field requirements.';
      error.textContent = `${this.controlLabel(control)}: ${hint}`;
      control.dataset['appErrorId'] = error.id;
      control.setAttribute('aria-invalid', 'true');
      control.setAttribute('aria-describedby', [control.getAttribute('aria-describedby'), error.id].filter(Boolean).join(' '));
      control.after(error);
    }
  }

  private invalidFieldLabels(form: HTMLFormElement): string[] {
    const controls = Array.from(form.querySelectorAll<HTMLElement>('input, select, textarea'))
      .filter((control) => this.isInvalidControl(control));
    const labels = controls.map((control) => this.controlLabel(control)).filter(Boolean);
    return Array.from(new Set(labels));
  }

  private isInvalidControl(control: HTMLElement): boolean {
    if (control instanceof HTMLInputElement && control.type === 'hidden') return false;
    if (control.hasAttribute('disabled')) return false;
    return control.classList.contains('ng-invalid') || ('validity' in control && !(control as HTMLInputElement).validity.valid);
  }

  private controlLabel(control: HTMLElement): string {
    const id = control.getAttribute('id');
    const explicitLabel = id ? this.document.querySelector(`label[for="${CSS.escape(id)}"]`)?.textContent : '';
    const wrappingLabelElement = control.closest('label');
    const structuredLabel = wrappingLabelElement?.querySelector<HTMLElement>('.field-label-row > span:first-child, :scope > span:first-child')?.textContent;
    const labelCopy = wrappingLabelElement?.cloneNode(true) as HTMLElement | undefined;
    labelCopy?.querySelectorAll('.app-field-error, input, select, textarea').forEach(node => node.remove());
    const wrappingLabel = labelCopy?.textContent;
    const raw =
      explicitLabel ||
      control.getAttribute('aria-label') ||
      structuredLabel ||
      wrappingLabel ||
      control.getAttribute('placeholder') ||
      control.getAttribute('formControlName') ||
      control.getAttribute('name') ||
      'Required field';
    return raw.replace(/\s*Required\s*/gi, ' ').replace(/\s+/g, ' ').trim();
  }

  private escapeHtml(value: string): string {
    return value.replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' })[char] || char);
  }

  private enhanceSearchableSelects(): void {
    const selects = Array.from(this.document.querySelectorAll<HTMLSelectElement>('select:not([data-app-select-search-bound])'));
    for (const select of selects) {
      if (select.multiple || select.closest('.no-app-select-search')) {
        select.dataset['appSelectSearchBound'] = 'true';
        continue;
      }
      if (select.options.length < 20) continue;
      select.dataset['appSelectSearchBound'] = 'true';
      const search = this.document.createElement('input');
      search.type = 'search';
      search.className = 'app-select-search';
      search.placeholder = `Search ${this.controlLabel(select).toLowerCase() || 'options'}`;
      search.setAttribute('aria-label', search.placeholder);
      search.addEventListener('input', () => this.filterSelectOptions(select, search.value));
      select.before(search);
    }
  }

  private filterSelectOptions(select: HTMLSelectElement, query: string): void {
    const normalized = query.trim().toLowerCase();
    for (const option of Array.from(select.options)) {
      const alwaysShow = !option.value;
      option.hidden = !alwaysShow && !!normalized && !option.text.toLowerCase().includes(normalized);
    }
  }
}
