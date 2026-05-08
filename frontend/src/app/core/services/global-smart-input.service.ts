import { DOCUMENT } from '@angular/common';
import { inject, Injectable, NgZone } from '@angular/core';

type SuggestionGroup = {
  patterns: string[];
  items: string[];
};

@Injectable({ providedIn: 'root' })
export class GlobalSmartInputService {
  private readonly document = inject(DOCUMENT);
  private readonly zone = inject(NgZone);
  private observer: MutationObserver | null = null;
  private started = false;
  private readonly storagePrefix = 'hms:smart-input:';

  private readonly groups: SuggestionGroup[] = [
    { patterns: ['chief complaint', 'complaint', 'symptom'], items: ['Fever', 'Cough', 'Chest pain', 'Breathlessness', 'Abdominal pain', 'Vomiting', 'Headache', 'Dizziness', 'Trauma', 'Weakness'] },
    { patterns: ['diagnosis', 'dx'], items: ['Acute febrile illness', 'Upper respiratory tract infection', 'Hypertension', 'Type 2 diabetes mellitus', 'Gastritis', 'Acute abdomen under evaluation', 'Chest pain under evaluation', 'Bronchial asthma exacerbation'] },
    { patterns: ['advice'], items: ['Take adequate fluid', 'Return if symptoms worsen', 'Follow up with reports', 'Avoid oily/spicy food', 'Continue regular medications', 'Rest for 3 days'] },
    { patterns: ['note', 'remarks', 'remark', 'reason'], items: ['Urgent review requested', 'Patient clinically stable', 'Discussed with attendant', 'Pending consultant review', 'Repeat vitals advised', 'Follow hospital protocol'] },
    { patterns: ['department'], items: ['Emergency', 'General OPD', 'Medicine', 'Surgery', 'Pediatrics', 'Gynecology', 'Orthopedics', 'Cardiology', 'Radiology', 'Laboratory'] },
    { patterns: ['ward', 'room', 'bed', 'zone', 'location'], items: ['Triage', 'Resuscitation', 'Observation', 'Treatment', 'Minor procedure', 'Waiting', 'Cabin', 'General Ward', 'ICU', 'HDU'] },
    { patterns: ['medicine', 'drug'], items: ['Paracetamol', 'Cetirizine', 'Omeprazole', 'Salbutamol nebulization', 'Normal saline', 'ORS', 'Cefixime', 'Azithromycin', 'Metformin', 'Amlodipine'] },
    { patterns: ['investigation', 'test', 'lab', 'radiology', 'imaging'], items: ['CBC', 'RBS', 'Serum Creatinine', 'Electrolytes', 'Urine R/E', 'ECG', 'Troponin-I', 'Chest X-ray', 'USG Whole Abdomen', 'CT Brain'] },
    { patterns: ['supplier', 'vendor'], items: ['Primary medicine supplier', 'Emergency purchase supplier', 'Local diagnostic vendor', 'Medical equipment supplier'] },
    { patterns: ['inventory', 'item', 'store'], items: ['Main Store', 'Emergency Store', 'Pharmacy Store', 'OT Store', 'Ward Store', 'Consumables', 'PPE', 'IV fluids'] },
    { patterns: ['employee', 'staff'], items: ['Doctor', 'Nurse', 'Technician', 'Pharmacist', 'Receptionist', 'Billing officer'] },
    { patterns: ['payment method', 'method'], items: ['Cash', 'Card', 'Mobile banking', 'Bank transfer', 'Insurance', 'Credit'] },
    { patterns: ['discount'], items: ['No discount', 'Staff discount', 'Poor patient support', 'Management approval', 'Package adjustment'] },
  ];

  start(): void {
    if (this.started) return;
    this.started = true;
    this.zone.runOutsideAngular(() => {
      this.enhanceInputs();
      this.document.addEventListener('focusin', this.handleFocusIn, true);
      this.document.addEventListener('change', this.handleChange, true);
      this.observer = new MutationObserver(() => this.enhanceInputs());
      this.observer.observe(this.document.body, { childList: true, subtree: true });
    });
  }

  private readonly handleFocusIn = (event: Event): void => {
    const target = event.target;
    if (target instanceof HTMLTextAreaElement) {
      this.showTextAreaSuggestions(target);
    }
    if (target instanceof HTMLInputElement) {
      this.refreshDatalist(target);
    }
  };

  private readonly handleChange = (event: Event): void => {
    const target = event.target;
    if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement) {
      this.storeRecentValue(target);
    }
  };

  private enhanceInputs(): void {
    const inputs = Array.from(this.document.querySelectorAll<HTMLInputElement>('input:not([data-smart-input-bound])'));
    for (const input of inputs) {
      if (!this.isAutocompleteCandidate(input)) continue;
      input.dataset['smartInputBound'] = 'true';
      const datalist = this.ensureDatalist(input);
      input.setAttribute('list', datalist.id);
      input.setAttribute('autocomplete', input.getAttribute('autocomplete') || 'off');
      this.refreshDatalist(input);
    }

    const textareas = Array.from(this.document.querySelectorAll<HTMLTextAreaElement>('textarea:not([data-smart-input-bound])'));
    for (const textarea of textareas) {
      textarea.dataset['smartInputBound'] = 'true';
    }
  }

  private isAutocompleteCandidate(input: HTMLInputElement): boolean {
    if (input.disabled || input.readOnly || input.type === 'hidden' || input.type === 'password' || input.type === 'file') return false;
    if (input.hasAttribute('list') || input.closest('.no-smart-input')) return false;
    return ['text', 'search', 'tel', 'email', 'number', ''].includes(input.type);
  }

  private ensureDatalist(input: HTMLInputElement): HTMLDataListElement {
    const existingId = input.dataset['smartInputListId'];
    if (existingId) {
      const existing = this.document.getElementById(existingId);
      if (existing instanceof HTMLDataListElement) return existing;
    }
    const datalist = this.document.createElement('datalist');
    datalist.id = `smart-list-${Math.random().toString(36).slice(2)}`;
    input.dataset['smartInputListId'] = datalist.id;
    input.after(datalist);
    return datalist;
  }

  private refreshDatalist(input: HTMLInputElement): void {
    const listId = input.dataset['smartInputListId'];
    const datalist = listId ? this.document.getElementById(listId) : null;
    if (!(datalist instanceof HTMLDataListElement)) return;
    datalist.innerHTML = '';
    for (const item of this.suggestionsFor(input).slice(0, 12)) {
      const option = this.document.createElement('option');
      option.value = item;
      datalist.appendChild(option);
    }
  }

  private showTextAreaSuggestions(textarea: HTMLTextAreaElement): void {
    const suggestions = this.suggestionsFor(textarea).slice(0, 6);
    let strip = textarea.nextElementSibling instanceof HTMLElement && textarea.nextElementSibling.classList.contains('smart-suggestion-strip')
      ? textarea.nextElementSibling
      : null;
    if (!suggestions.length) {
      strip?.remove();
      return;
    }
    if (!strip) {
      strip = this.document.createElement('div');
      strip.className = 'smart-suggestion-strip';
      textarea.after(strip);
    }
    strip.innerHTML = '';
    for (const suggestion of suggestions) {
      const button = this.document.createElement('button');
      button.type = 'button';
      button.textContent = suggestion;
      button.addEventListener('mousedown', (event) => {
        event.preventDefault();
        textarea.value = textarea.value.trim() ? `${textarea.value.trim()}\n${suggestion}` : suggestion;
        textarea.dispatchEvent(new Event('input', { bubbles: true }));
        textarea.dispatchEvent(new Event('change', { bubbles: true }));
      });
      strip.appendChild(button);
    }
  }

  private suggestionsFor(control: HTMLInputElement | HTMLTextAreaElement): string[] {
    const key = this.fieldKey(control);
    const staticItems = this.groups
      .filter((group) => group.patterns.some((pattern) => key.includes(pattern)))
      .flatMap((group) => group.items);
    return Array.from(new Set([...this.recentValues(key), ...staticItems])).slice(0, 16);
  }

  private storeRecentValue(control: HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement): void {
    const value = control instanceof HTMLSelectElement ? control.selectedOptions.item(0)?.textContent?.trim() || '' : control.value.trim();
    if (!value || value.length < 2 || value.length > 90) return;
    const key = this.fieldKey(control);
    if (!key) return;
    const values = [value, ...this.recentValues(key).filter((item) => item.toLowerCase() !== value.toLowerCase())].slice(0, 8);
    window.localStorage.setItem(`${this.storagePrefix}${key}`, JSON.stringify(values));
  }

  private recentValues(key: string): string[] {
    try {
      const parsed = JSON.parse(window.localStorage.getItem(`${this.storagePrefix}${key}`) || '[]');
      return Array.isArray(parsed) ? parsed.map(String).filter(Boolean) : [];
    } catch {
      return [];
    }
  }

  private fieldKey(control: HTMLElement): string {
    const id = control.getAttribute('id');
    const label = id ? this.document.querySelector(`label[for="${CSS.escape(id)}"]`)?.textContent || '' : '';
    const wrappedLabel = control.closest('label')?.textContent || '';
    return [
      label,
      wrappedLabel,
      control.getAttribute('aria-label'),
      control.getAttribute('placeholder'),
      control.getAttribute('formControlName'),
      control.getAttribute('name'),
    ]
      .filter(Boolean)
      .join(' ')
      .replace(/\s*Required\s*/gi, ' ')
      .replace(/\s+/g, ' ')
      .trim()
      .toLowerCase();
  }
}
