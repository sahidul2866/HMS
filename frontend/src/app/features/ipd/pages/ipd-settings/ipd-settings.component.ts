import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { NotificationService } from '../../../../core/services/notification.service';
import { IPDBed } from '../../models/ipd.models';
import { IPDService } from '../../services/ipd.service';

@Component({
  selector: 'app-ipd-settings',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './ipd-settings.component.html',
  styleUrls: ['./ipd-settings.component.scss'],
})
export class IPDSettingsComponent {
  private readonly fb = inject(FormBuilder);
  private readonly ipdService = inject(IPDService);
  private readonly notificationService = inject(NotificationService);

  beds: IPDBed[] = [];

  readonly bedForm = this.fb.group({
    ward_name: ['Ward A', Validators.required],
    bed_number: ['', Validators.required],
    bed_type: ['General', Validators.required],
    daily_rate: [0, Validators.required],
    note: [''],
  });

  constructor() {
    this.loadBeds();
  }

  loadBeds(): void {
    this.ipdService.listBeds().subscribe((beds) => (this.beds = beds));
  }

  submitBed(): void {
    if (this.bedForm.invalid) {
      this.bedForm.markAllAsTouched();
      return;
    }
    this.ipdService.createBed(this.bedForm.getRawValue() as never).subscribe((bed) => {
      this.notificationService.success(`Bed ${bed.ward_name} / ${bed.bed_number} created.`);
      this.bedForm.reset({
        ward_name: this.bedForm.getRawValue().ward_name || 'Ward A',
        bed_number: '',
        bed_type: this.bedForm.getRawValue().bed_type || 'General',
        daily_rate: 0,
        note: '',
      });
      this.loadBeds();
    });
  }

  get wardOptions(): string[] {
    return [...new Set(this.beds.map((bed) => bed.ward_name).filter(Boolean))].sort((a, b) => a.localeCompare(b));
  }

  get bedTypeOptions(): string[] {
    return [...new Set(this.beds.map((bed) => bed.bed_type).filter(Boolean))].sort((a, b) => a.localeCompare(b));
  }
}
