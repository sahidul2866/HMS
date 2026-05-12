import { Injectable, computed, signal } from '@angular/core';

export interface CommandPaletteContext {
  module?: string;
  action?: string;
}

@Injectable({ providedIn: 'root' })
export class CommandPaletteService {
  private readonly openSignal = signal(false);
  private readonly contextSignal = signal<CommandPaletteContext>({});

  readonly open = this.openSignal.asReadonly();
  readonly context = this.contextSignal.asReadonly();
  readonly closed = computed(() => !this.openSignal());

  show(context: CommandPaletteContext = {}): void {
    this.contextSignal.set(context);
    this.openSignal.set(true);
  }

  hide(): void {
    this.openSignal.set(false);
  }

  toggle(context: CommandPaletteContext = {}): void {
    if (this.openSignal()) {
      this.hide();
    } else {
      this.show(context);
    }
  }
}

