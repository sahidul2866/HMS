import { DOCUMENT } from '@angular/common';
import { Component, NgZone, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { ThemeService } from './core/services/theme.service';
import { GlobalLoaderComponent } from './shared/components/global-loader/global-loader.component';
import { SyncUpdateBannerComponent } from './shared/components/sync-update-banner/sync-update-banner.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, GlobalLoaderComponent, SyncUpdateBannerComponent],
  templateUrl: './app.component.html',
})
export class AppComponent {
  private readonly themeService = inject(ThemeService);
  private readonly document = inject(DOCUMENT);
  private readonly zone = inject(NgZone);

  constructor() {
    this.themeService.initialize();
    this.initializeRowActionMenus();
  }

  private initializeRowActionMenus(): void {
    this.zone.runOutsideAngular(() => {
      this.document.addEventListener('toggle', (event) => {
        const menu = event.target;
        if (!(menu instanceof HTMLDetailsElement) || !menu.classList.contains('row-action-menu') || !menu.open) {
          return;
        }
        this.closeRowActionMenus(menu);
      }, true);

      this.document.addEventListener('pointerdown', (event) => {
        const target = event.target as Element | null;
        if (target?.closest('.row-action-menu')) return;
        this.closeRowActionMenus();
      }, true);

      this.document.addEventListener('click', (event) => {
        const target = event.target as Element | null;
        const menu = target?.closest<HTMLDetailsElement>('details.row-action-menu');
        if (!menu || target?.closest('summary')) return;
        if (target?.closest('button, a')) {
          menu.open = false;
        }
      }, true);

      this.document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
          this.closeRowActionMenus();
        }
      });
    });
  }

  private closeRowActionMenus(except?: HTMLDetailsElement): void {
    this.document.querySelectorAll<HTMLDetailsElement>('details.row-action-menu[open]').forEach((menu) => {
      if (menu !== except) {
        menu.open = false;
      }
    });
  }
}
