import { CommonModule } from '@angular/common';
import { Component, DestroyRef, effect, inject, signal } from '@angular/core';

import { LoadingService } from '../../../core/services/loading.service';

@Component({
  selector: 'app-global-loader',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './global-loader.component.html',
  styleUrl: './global-loader.component.scss',
})
export class GlobalLoaderComponent {
  readonly loadingService = inject(LoadingService);
  readonly elapsedSeconds = signal(0);

  private readonly destroyRef = inject(DestroyRef);
  private timerId: ReturnType<typeof setInterval> | null = null;

  constructor() {
    effect(() => {
      if (this.loadingService.isLoading() > 0) {
        this.startTimer();
        return;
      }

      this.stopTimer();
    });

    this.destroyRef.onDestroy(() => this.stopTimer());
  }

  private startTimer(): void {
    if (this.timerId !== null) {
      return;
    }

    this.elapsedSeconds.set(0);
    this.timerId = setInterval(() => {
      this.elapsedSeconds.update((seconds) => seconds + 1);
    }, 1000);
  }

  private stopTimer(): void {
    if (this.timerId !== null) {
      clearInterval(this.timerId);
      this.timerId = null;
    }

    this.elapsedSeconds.set(0);
  }
}
