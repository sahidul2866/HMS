import { Injectable, signal } from '@angular/core';

export type NotificationLevel = 'success' | 'error' | 'warning' | 'info';

export interface NotificationItem {
  id: number;
  level: NotificationLevel;
  message: string;
  createdAt: number;
  durationMs: number;
}

@Injectable({ providedIn: 'root' })
export class NotificationService {
  private readonly itemsSignal = signal<NotificationItem[]>([]);
  private nextId = 1;

  readonly items = this.itemsSignal.asReadonly();

  success(message: string, nextStep = ''): void {
    this.push('success', [message,nextStep].filter(Boolean).join(' '));
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
    if (this.itemsSignal().some(item => item.level === level && item.message === message)) return;
    const id = this.nextId++;
    const durationMs = level === 'error' || level === 'warning' ? 12000 : 4500;
    this.itemsSignal.update((items) => [...items.slice(-2), { id, level, message, createdAt: Date.now(), durationMs }]);
    window.setTimeout(() => this.dismiss(id), durationMs);
  }
}
