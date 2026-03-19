import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';

import { SessionService } from '../../../../core/services/session.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './dashboard.component.html',
})
export class DashboardComponent {
  readonly session = inject(SessionService);
}

