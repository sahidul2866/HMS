import { Component, inject } from '@angular/core';
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

  constructor() {
    this.themeService.initialize();
  }
}
