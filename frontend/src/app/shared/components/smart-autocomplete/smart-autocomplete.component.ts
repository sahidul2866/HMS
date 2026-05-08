import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output, forwardRef } from '@angular/core';
import { ControlValueAccessor, FormsModule, NG_VALUE_ACCESSOR } from '@angular/forms';

export type SmartAutocompleteOption = {
  label: string;
  value: string;
  meta?: string;
};

@Component({
  selector: 'app-smart-autocomplete',
  standalone: true,
  imports: [CommonModule, FormsModule],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => SmartAutocompleteComponent),
      multi: true,
    },
  ],
  template: `
    <div class="smart-input">
      <input
        [attr.placeholder]="placeholder"
        [disabled]="disabled"
        [ngModel]="query"
        (ngModelChange)="onQueryChange($event)"
        (focus)="open = true"
        (keydown.enter)="selectFirst($event)"
        (blur)="closeSoon()"
      />
      <div class="smart-menu" *ngIf="open && filteredOptions.length">
        <button type="button" *ngFor="let option of filteredOptions" (mousedown)="select(option)">
          <strong>{{ option.label }}</strong>
          <span *ngIf="option.meta">{{ option.meta }}</span>
        </button>
      </div>
    </div>
  `,
  styles: [
    '.smart-input { position: relative; display: grid; }',
    'input { width: 100%; border: 1px solid var(--border); border-radius: 8px; padding: .58rem .68rem; background: var(--surface); color: var(--text); }',
    '.smart-menu { position: absolute; top: calc(100% + .25rem); left: 0; right: 0; z-index: 40; display: grid; max-height: 240px; overflow: auto; border: 1px solid var(--border); border-radius: 8px; background: var(--surface); box-shadow: 0 16px 34px rgba(15, 23, 42, .14); }',
    '.smart-menu button { display: grid; gap: .12rem; border: 0; border-bottom: 1px solid color-mix(in srgb, var(--border) 72%, transparent); padding: .55rem .65rem; background: transparent; color: var(--text); text-align: left; }',
    '.smart-menu button:hover { background: color-mix(in srgb, var(--primary) 7%, var(--surface)); }',
    '.smart-menu span { color: var(--text-muted); font-size: .78rem; }',
  ],
})
export class SmartAutocompleteComponent implements ControlValueAccessor {
  @Input() placeholder = 'Search';
  @Input() options: SmartAutocompleteOption[] = [];
  @Input() maxVisible = 8;
  @Output() selected = new EventEmitter<SmartAutocompleteOption>();

  query = '';
  disabled = false;
  open = false;
  private onChange: (value: string) => void = () => undefined;
  private onTouched: () => void = () => undefined;

  get filteredOptions(): SmartAutocompleteOption[] {
    const normalized = this.query.trim().toLowerCase();
    const source = normalized ? this.options.filter((item) => `${item.label} ${item.meta || ''}`.toLowerCase().includes(normalized)) : this.options;
    return source.slice(0, this.maxVisible);
  }

  writeValue(value: string | null): void {
    this.query = value || '';
  }

  registerOnChange(fn: (value: string) => void): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this.onTouched = fn;
  }

  setDisabledState(isDisabled: boolean): void {
    this.disabled = isDisabled;
  }

  onQueryChange(value: string): void {
    this.query = value;
    this.open = true;
    this.onChange(value);
  }

  select(option: SmartAutocompleteOption): void {
    this.query = option.value;
    this.onChange(option.value);
    this.selected.emit(option);
    this.open = false;
  }

  selectFirst(event: Event): void {
    const first = this.filteredOptions[0];
    if (!first) return;
    event.preventDefault();
    this.select(first);
  }

  closeSoon(): void {
    this.onTouched();
    window.setTimeout(() => (this.open = false), 150);
  }
}
