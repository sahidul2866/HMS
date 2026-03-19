import { Injectable, signal } from '@angular/core';

export type NotificationLevel = 'success' | 'error' | 'warning' | 'info';

export interface NotificationItem {
  id: number;
  level: NotificationLevel;
  message: string;
}

@Injectable({ providedIn: 'root' })
export class NotificationService {
  private readonly itemsSignal = signal<NotificationItem[]>([]);
  private nextId = 1;

  readonly items = this.itemsSignal.asReadonly();

  success(message: string): void {
    this.push('success', message);
  }

  error(message: string): void {
    this.push('error', message);
  }

  warning(message: string): void {
    this.push('warning', message);
  }

  info(message: string): void {
    this.push('info', message);
  }

  dismiss(id: number): void {
    this.itemsSignal.update((items) => items.filter((item) => item.id !== id));
  }

  private push(level: NotificationLevel, message: string): void {
    const id = this.nextId++;
    this.itemsSignal.update((items) => [...items, { id, level, message }]);
    window.setTimeout(() => this.dismiss(id), 4500);
  }
}
