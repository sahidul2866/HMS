import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';

import { DataSyncService } from '../../../core/services/data-sync.service';

@Component({
  selector: 'app-sync-update-banner',
  standalone: true,
  imports: [CommonModule],
  template: `
    <aside class="sync-banner" *ngIf="dataSync.hasPendingUpdates()">
      <div>
        <strong>Newer data available</strong>
        <span>{{ dataSync.pendingMessage() }}</span>
      </div>
      <button type="button" (click)="dataSync.requestRefresh()">Refresh data</button>
      <button type="button" class="ghost" (click)="dataSync.dismissAll()">Dismiss</button>
    </aside>
  `,
  styles: [
    '.sync-banner { position: fixed; right: 1rem; bottom: 1rem; z-index: 2600; display: flex; gap: .75rem; align-items: center; max-width: min(620px, calc(100vw - 2rem)); border: 1px solid color-mix(in srgb, var(--primary) 28%, var(--border)); border-radius: 8px; padding: .75rem; background: var(--surface); color: var(--text); box-shadow: 0 18px 42px rgba(15, 23, 42, .18); }',
    '.sync-banner div { display: grid; gap: .1rem; min-width: 0; }',
    '.sync-banner span { color: var(--text-muted); font-size: .84rem; }',
    '.sync-banner button { border: 1px solid var(--border); border-radius: 8px; padding: .45rem .65rem; background: var(--primary); color: #fff; font-weight: 800; white-space: nowrap; }',
    '.sync-banner button.ghost { background: var(--surface); color: var(--text); }',
    '@media (max-width: 640px) { .sync-banner { left: .75rem; right: .75rem; bottom: .75rem; align-items: stretch; flex-direction: column; } }',
  ],
})
export class SyncUpdateBannerComponent {
  readonly dataSync = inject(DataSyncService);
}
