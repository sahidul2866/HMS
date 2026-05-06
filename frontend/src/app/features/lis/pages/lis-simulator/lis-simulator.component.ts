import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';

import { NotificationService } from '../../../../core/services/notification.service';
import { LISMachine, LISQueueItem, LISSimulationResult } from '../../models/lis.models';
import { LISServiceApi } from '../../services/lis.service';

@Component({
  selector: 'app-lis-simulator',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './lis-simulator.component.html',
  styleUrl: './lis-simulator.component.scss',
})
export class LISSimulatorComponent {
  private readonly lisService = inject(LISServiceApi);
  private readonly notificationService = inject(NotificationService);

  machines: LISMachine[] = [];
  queue: LISQueueItem[] = [];
  selectedMachineCode = '';
  runningOrderId = '';
  logs: LISSimulationResult[] = [];

  constructor() {
    this.refresh();
  }

  refresh(): void {
    this.lisService.listMachines().subscribe((machines) => {
      this.machines = machines;
      if (!this.selectedMachineCode && this.onlineMachines.length) {
        this.selectedMachineCode = this.onlineMachines[0].code;
      }
    });
    this.lisService.listQueue().subscribe((queue) => {
      this.queue = queue;
    });
  }

  pickMachine(code: string): void {
    this.selectedMachineCode = code;
  }

  simulate(item: LISQueueItem): void {
    if (!this.selectedMachineCode || this.runningOrderId) {
      return;
    }
    this.runningOrderId = item.order_id;
    this.lisService
      .simulateAnalyze({
        machine_code: this.selectedMachineCode,
        order_id: item.order_id,
      })
      .subscribe({
        next: (result) => {
          this.logs = [result, ...this.logs].slice(0, 12);
          this.notificationService.success(`Analysis completed: ${result.machine_name}`);
          this.runningOrderId = '';
          this.refresh();
        },
        error: () => {
          this.runningOrderId = '';
          this.notificationService.error('Machine simulation failed.');
        },
      });
  }

  get onlineMachines(): LISMachine[] {
    return this.machines.filter((machine) => machine.status === 'online');
  }
}
