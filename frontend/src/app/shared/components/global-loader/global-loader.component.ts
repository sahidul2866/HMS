import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';

import { LoadingService } from '../../../core/services/loading.service';

@Component({
  selector: 'app-global-loader',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './global-loader.component.html',
})
export class GlobalLoaderComponent {
  readonly loadingService = inject(LoadingService);
}
