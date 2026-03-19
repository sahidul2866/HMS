import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';

@Component({
  selector: 'app-radiology-overview',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './radiology-overview.component.html',
})
export class RadiologyOverviewComponent {
  readonly imagingQueue = [
    { label: 'Studies Scheduled', value: '11' },
    { label: 'Reports Awaiting Sign-off', value: '4' },
    { label: 'Average Turnaround', value: '38 min' },
  ];
}
