import { CommonModule } from '@angular/common';
import { Component, EventEmitter, HostListener, Input, Output, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

import { NotificationService } from '../../../core/services/notification.service';
import { ScanResolvedRecord } from '../../../features/scanner/models/scanner.models';
import { ScannerService } from '../../../features/scanner/services/scanner.service';
import { printScanLabel } from '../../utils/scan-print.utils';

@Component({
  selector: 'app-global-scanner',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './global-scanner.component.html',
  styleUrls: ['./global-scanner.component.scss'],
})
export class GlobalScannerComponent {
  private readonly scanner = inject(ScannerService);
  private readonly router = inject(Router);
  private readonly notifications = inject(NotificationService);

  @Input() compact = false;
  @Input() module = 'global';
  @Input() action = 'lookup';
  @Output() recordSelected = new EventEmitter<ScanResolvedRecord>();

  open = false;
  code = '';
  loading = false;
  message = '';
  records: ScanResolvedRecord[] = [];
  cameraActive = false;
  cameraSupported = typeof navigator.mediaDevices?.getUserMedia === 'function' && !!(window as any).BarcodeDetector;
  private lastCode = '';
  private lastScanAt = 0;
  private keyboardBuffer = '';
  private bufferTimer?: number;
  private cameraStream?: MediaStream;
  private cameraTimer?: number;

  @HostListener('window:keydown', ['$event'])
  onKeydown(event: KeyboardEvent): void {
    if (event.altKey && event.key.toLowerCase() === 'b') {
      event.preventDefault();
      this.show();
      return;
    }
    if (this.open || event.ctrlKey || event.metaKey || event.altKey || this.isTypingTarget(event.target)) {
      return;
    }
    if (event.key === 'Enter' && this.keyboardBuffer.length >= 4) {
      event.preventDefault();
      this.code = this.keyboardBuffer;
      this.keyboardBuffer = '';
      this.resolve();
      return;
    }
    if (event.key.length === 1) {
      this.keyboardBuffer += event.key;
      window.clearTimeout(this.bufferTimer);
      this.bufferTimer = window.setTimeout(() => (this.keyboardBuffer = ''), 90);
    }
  }

  show(): void {
    this.open = true;
    this.message = '';
    this.records = [];
    setTimeout(() => document.getElementById('global-scan-input')?.focus(), 20);
  }

  close(): void {
    this.stopCamera();
    this.open = false;
    this.code = '';
    this.records = [];
  }

  resolve(): void {
    const trimmed = this.code.trim();
    if (!trimmed) return;
    const now = Date.now();
    if (trimmed === this.lastCode && now - this.lastScanAt < 1200) {
      this.message = 'Duplicate scan ignored';
      return;
    }
    this.lastCode = trimmed;
    this.lastScanAt = now;
    this.loading = true;
    this.scanner.resolve({ code: trimmed, module: this.module, action: this.action }).subscribe({
      next: (response) => {
        this.loading = false;
        this.message = response.message;
        this.records = response.records;
        if (response.records.length === 1) this.select(response.records[0]);
      },
      error: (error) => {
        this.loading = false;
        this.records = [];
        this.message = error?.error?.message || 'Scan failed';
        this.notifications.error(this.message);
      },
    });
  }

  select(record: ScanResolvedRecord): void {
    this.recordSelected.emit(record);
    this.notifications.success(`${record.display} loaded`);
    if (record.route) {
      void this.router.navigate([record.route], { queryParams: { scan: record.record_id, scanType: record.record_type } });
    }
    this.close();
  }

  print(record: ScanResolvedRecord): void {
    printScanLabel({
      title: record.display,
      subtitle: record.record_type.replaceAll('_', ' '),
      code: this.code,
      kind: record.record_type === 'ipd_admission' || record.record_type === 'er_visit' ? 'wristband' : 'label',
      lines: Object.entries(record.data).slice(0, 4).map(([key, value]) => `${key.replaceAll('_', ' ')}: ${value ?? '-'}`),
    });
  }

  startCamera(): void {
    if (!this.cameraSupported) {
      this.message = 'Camera scanning is not available in this browser';
      return;
    }
    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: 'environment' } })
      .then((stream) => {
        this.cameraStream = stream;
        this.cameraActive = true;
        const video = document.getElementById('global-scan-video') as HTMLVideoElement | null;
        if (video) {
          video.srcObject = stream;
          void video.play();
        }
        this.scanCameraFrame();
      })
      .catch(() => (this.message = 'Unable to open camera'));
  }

  stopCamera(): void {
    window.clearTimeout(this.cameraTimer);
    this.cameraStream?.getTracks().forEach((track) => track.stop());
    this.cameraStream = undefined;
    this.cameraActive = false;
  }

  private scanCameraFrame(): void {
    if (!this.cameraActive) return;
    const video = document.getElementById('global-scan-video') as HTMLVideoElement | null;
    const Detector = (window as any).BarcodeDetector;
    if (!video || !Detector || video.readyState < 2) {
      this.cameraTimer = window.setTimeout(() => this.scanCameraFrame(), 300);
      return;
    }
    const detector = new Detector({ formats: ['qr_code', 'code_128', 'code_39', 'ean_13'] });
    detector
      .detect(video)
      .then((codes: Array<{ rawValue: string }>) => {
        if (codes.length && codes[0].rawValue) {
          this.code = codes[0].rawValue;
          this.stopCamera();
          this.resolve();
          return;
        }
        this.cameraTimer = window.setTimeout(() => this.scanCameraFrame(), 300);
      })
      .catch(() => {
        this.stopCamera();
        this.message = 'Camera scan failed';
      });
  }

  private isTypingTarget(target: EventTarget | null): boolean {
    const element = target as HTMLElement | null;
    return !!element && ['INPUT', 'TEXTAREA', 'SELECT'].includes(element.tagName);
  }
}
