import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';

@Component({
  selector: 'app-laboratory-overview',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './laboratory-overview.component.html',
})
export class LaboratoryOverviewComponent {
  readonly worklist = [
    { label: 'Samples Awaiting Accession', value: '14' },
    { label: 'Critical Results Pending', value: '3' },
    { label: 'Turnaround Compliance', value: '92%' },
  ];
}
