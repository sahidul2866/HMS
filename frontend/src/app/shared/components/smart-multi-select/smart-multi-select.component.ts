import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';

export type SmartMultiSelectOption = {
  label: string;
  value: string;
  meta?: string;
};

@Component({
  selector: 'app-smart-multi-select',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="smart-multi">
      <div class="tag-row" *ngIf="value.length">
        <button type="button" *ngFor="let selected of selectedOptions" (click)="remove(selected.value)">
          {{ selected.label }} <span aria-hidden="true">x</span>
        </button>
      </div>
      <input
        type="search"
        [(ngModel)]="query"
        [placeholder]="placeholder"
        (focus)="open = true"
        (keydown.enter)="addFirst($event)"
        (blur)="closeSoon()"
      />
      <div class="smart-menu" *ngIf="open && filteredOptions.length">
        <button type="button" *ngFor="let option of filteredOptions" (mousedown)="toggle(option)">
          <strong>{{ option.label }}</strong>
          <span *ngIf="option.meta">{{ option.meta }}</span>
        </button>
      </div>
    </div>
  `,
  styles: [
    '.smart-multi { position: relative; display: grid; gap: .35rem; }',
    '.tag-row { display: flex; flex-wrap: wrap; gap: .35rem; }',
    '.tag-row button { border: 1px solid color-mix(in srgb, var(--primary) 28%, var(--border)); border-radius: 999px; padding: .28rem .48rem; background: color-mix(in srgb, var(--primary) 7%, var(--surface)); color: var(--primary); font-weight: 800; }',
    'input { width: 100%; border: 1px solid var(--border); border-radius: 8px; padding: .58rem .68rem; background: var(--surface); color: var(--text); }',
    '.smart-menu { position: absolute; top: calc(100% + .25rem); left: 0; right: 0; z-index: 40; display: grid; max-height: 240px; overflow: auto; border: 1px solid var(--border); border-radius: 8px; background: var(--surface); box-shadow: 0 16px 34px rgba(15, 23, 42, .14); }',
    '.smart-menu button { display: grid; gap: .12rem; border: 0; border-bottom: 1px solid color-mix(in srgb, var(--border) 72%, transparent); padding: .55rem .65rem; background: transparent; color: var(--text); text-align: left; }',
    '.smart-menu button:hover { background: color-mix(in srgb, var(--primary) 7%, var(--surface)); }',
    '.smart-menu span { color: var(--text-muted); font-size: .78rem; }',
  ],
})
export class SmartMultiSelectComponent {
  @Input() placeholder = 'Search and add';
  @Input() options: SmartMultiSelectOption[] = [];
  @Input() value: string[] = [];
  @Input() maxVisible = 8;
  @Output() valueChange = new EventEmitter<string[]>();

  query = '';
  open = false;

  get selectedOptions(): SmartMultiSelectOption[] {
    return this.value.map((item) => this.options.find((option) => option.value === item) || { label: item, value: item });
  }

  get filteredOptions(): SmartMultiSelectOption[] {
    const normalized = this.query.trim().toLowerCase();
    return this.options
      .filter((option) => !this.value.includes(option.value))
      .filter((option) => !normalized || `${option.label} ${option.meta || ''}`.toLowerCase().includes(normalized))
      .slice(0, this.maxVisible);
  }

  toggle(option: SmartMultiSelectOption): void {
    this.value = [...this.value, option.value];
    this.valueChange.emit(this.value);
    this.query = '';
  }

  remove(value: string): void {
    this.value = this.value.filter((item) => item !== value);
    this.valueChange.emit(this.value);
  }

  addFirst(event: Event): void {
    const first = this.filteredOptions[0];
    if (!first) return;
    event.preventDefault();
    this.toggle(first);
  }

  closeSoon(): void {
    window.setTimeout(() => (this.open = false), 150);
  }
}
