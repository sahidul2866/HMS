import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { ScanSetting } from '../../models/scanner.models';
import { ScannerService } from '../../services/scanner.service';

@Component({
  selector: 'app-scanner-settings',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './scanner-settings.component.html',
  styleUrls: ['./scanner-settings.component.scss'],
})
export class ScannerSettingsComponent {
  private readonly scanner = inject(ScannerService);

  settings: ScanSetting[] = [];
  message = '';
  form = {
    setting_key: 'global',
    barcode_type: 'code128',
    qr_format: 'HMS:{purpose}:{record_type}:{token}',
    patient_card_format: 'PATIENT_CARD_V1',
    wristband_format: 'WRISTBAND_V1',
    label_size: '50x25mm',
    lab_sample_label: 'LAB_SAMPLE_V1',
    blood_unit_label: 'BLOOD_UNIT_V1',
    inventory_item_label: 'INV_ITEM_V1',
    invoice_qr_format: 'INVOICE_VERIFY_V1',
    document_qr_format: 'DOC_VERIFY_V1',
    printer_name: '',
    auto_print: false,
  };

  constructor() {
    this.load();
  }

  load(): void {
    this.scanner.listSettings().subscribe((settings) => (this.settings = settings));
  }

  save(): void {
    const { setting_key, ...setting_value } = this.form;
    this.scanner.saveSetting({ setting_key, setting_value }).subscribe({
      next: () => {
        this.message = 'Scanner settings saved';
        this.load();
      },
      error: (error) => (this.message = error?.error?.message || 'Unable to save settings'),
    });
  }
}

