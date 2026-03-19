import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { HasPermissionDirective } from '../../../../shared/directives/has-permission.directive';
import { SessionService } from '../../../../core/services/session.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink, HasPermissionDirective],
  templateUrl: './dashboard.component.html',
})
export class DashboardComponent {
  readonly session = inject(SessionService);
}
