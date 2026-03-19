import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';

import { TabService } from '../../../core/services/tab.service';

@Component({
  selector: 'app-tab-strip',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './tab-strip.component.html',
})
export class TabStripComponent {
  readonly tabService = inject(TabService);

  activate(path: string): void {
    this.tabService.activate(path);
  }

  close(event: MouseEvent, path: string): void {
    event.stopPropagation();
    this.tabService.close(path);
  }
}
