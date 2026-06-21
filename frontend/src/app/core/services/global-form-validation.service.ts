import { DOCUMENT } from '@angular/common';
import { inject, Injectable, NgZone } from '@angular/core';

import { NotificationService } from './notification.service';

@Injectable({ providedIn: 'root' })
export class GlobalFormValidationService {
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
      this.document.addEventListener('click', this.handleClick, true);
      this.document.addEventListener('input', this.handleControlChange, true);
      this.document.addEventListener('change', this.handleControlChange, true);
      this.enhanceSearchableSelects();
      this.observer = new MutationObserver(() => this.enhanceSearchableSelects());
      this.observer.observe(this.document.body, { childList: true, subtree: true });
    });
  }

  private readonly handleSubmit = (event: Event): void => {
    const form = event.target instanceof HTMLFormElement ? event.target : null;
    if (!form || !this.isInvalidForm(form)) return;
    this.renderValidation(form);
  };

  private readonly handleClick = (event: Event): void => {
    const target = event.target instanceof Element ? event.target : null;
    const button = target?.closest('button');
    if (!button || button.type === 'submit') return;
    const form = button.closest('form');
    if (!form || !this.isInvalidForm(form)) return;
    this.renderValidation(form);
  };

  private readonly handleControlChange = (event: Event): void => {
    const target = event.target instanceof Element ? event.target : null;
    const form = target?.closest('form');
    if (!form) return;
    const summary = form.querySelector<HTMLElement>('.app-validation-summary');
    if (!summary) return;
    const missingFields = this.invalidFieldLabels(form);
    if (missingFields.length) {
      summary.innerHTML = `<strong>Required before saving:</strong><span>${this.escapeHtml(missingFields.join(', '))}</span>`;
      return;
    }
    form.classList.remove('app-form-submitted');
    summary.remove();
  };

  private isInvalidForm(form: HTMLFormElement): boolean {
    return form.classList.contains('ng-invalid') || !form.checkValidity();
  }

  private renderValidation(form: HTMLFormElement): void {
    form.classList.add('app-form-submitted');
    const missingFields = this.invalidFieldLabels(form);
    if (!missingFields.length) return;

    let summary = form.querySelector<HTMLElement>('.app-validation-summary');
    if (!summary) {
      summary = this.document.createElement('div');
      summary.className = 'app-validation-summary';
      summary.setAttribute('role', 'alert');
      form.prepend(summary);
    }
    summary.innerHTML = `<strong>Required before saving:</strong><span>${this.escapeHtml(missingFields.join(', '))}</span>`;
    summary.scrollIntoView({ block: 'center', behavior: 'smooth' });

    this.zone.run(() => {
      this.notificationService.error(`Required before saving: ${missingFields.join(', ')}`);
    });
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
    const wrappingLabel = wrappingLabelElement?.textContent;
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
      select.dataset['appSelectSearchBound'] = 'true';
      if (select.multiple || select.options.length < 9 || select.closest('.no-app-select-search')) continue;
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
    const selected = select.selectedOptions.item(0);
    if (selected?.hidden) {
      select.value = '';
      select.dispatchEvent(new Event('change', { bubbles: true }));
    }
  }
}
