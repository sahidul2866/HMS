import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { GlobalLoaderComponent } from './shared/components/global-loader/global-loader.component';
import { NotificationCenterComponent } from './shared/components/notification-center/notification-center.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, GlobalLoaderComponent, NotificationCenterComponent],
  templateUrl: './app.component.html',
})
export class AppComponent {}
