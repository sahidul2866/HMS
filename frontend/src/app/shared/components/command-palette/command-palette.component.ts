import { CommonModule } from '@angular/common';
import { Component, ElementRef, HostListener, ViewChild, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

import { CommandPaletteService } from '../../../core/services/command-palette.service';
import { NotificationService } from '../../../core/services/notification.service';
import { SessionService } from '../../../core/services/session.service';
import { ScanResolvedRecord } from '../../../features/scanner/models/scanner.models';
import { ScannerService } from '../../../features/scanner/services/scanner.service';
import { MenuItem, menuConfig } from '../../../navigation/menu.config';

interface CommandItem {
  label: string;
  description: string;
  route?: string;
  keywords: string;
  permissions: string[];
  action?: () => void;
}

@Component({
  selector: 'app-command-palette',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './command-palette.component.html',
  styleUrls: ['./command-palette.component.scss'],
})
export class CommandPaletteComponent {
  readonly palette = inject(CommandPaletteService);
  private readonly session = inject(SessionService);
  private readonly router = inject(Router);
  private readonly scanner = inject(ScannerService);
  private readonly notifications = inject(NotificationService);

  @ViewChild('searchBox') searchBox?: ElementRef<HTMLInputElement>;

  query = signal('');
  selectedIndex = signal(0);
  scanning = false;
  scanRecords: ScanResolvedRecord[] = [];

  commands = computed(() => this.visibleCommands());
  filtered = computed(() => {
    const term = this.query().trim().toLowerCase();
    const commands = this.commands();
    if (!term) return commands.slice(0, 14);
    return commands.filter((item) => `${item.label} ${item.description} ${item.keywords}`.toLowerCase().includes(term)).slice(0, 14);
  });

  @HostListener('window:keydown', ['$event'])
  onWindowKeydown(event: KeyboardEvent): void {
    const key = event.key.toLowerCase();
    if ((event.ctrlKey || event.metaKey) && key === 'k') {
      event.preventDefault();
      this.open();
      return;
    }
    if ((event.ctrlKey || event.metaKey) && key === '/') {
      event.preventDefault();
      this.open('?');
      return;
    }
    if (!this.palette.open()) return;
    if (event.key === 'Escape') {
      event.preventDefault();
      this.close();
      return;
    }
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      this.move(event.key === 'ArrowDown' ? 1 : -1);
      return;
    }
    if (event.key === 'Enter') {
      event.preventDefault();
      this.activateSelected();
    }
  }

  open(initialQuery = ''): void {
    this.query.set(initialQuery);
    this.selectedIndex.set(0);
    this.scanRecords = [];
    this.palette.show();
    setTimeout(() => this.searchBox?.nativeElement.focus(), 20);
  }

  close(): void {
    this.palette.hide();
    this.query.set('');
    this.scanRecords = [];
  }

  move(delta: 1 | -1): void {
    const count = this.scanRecords.length || this.filtered().length;
    if (!count) return;
    this.selectedIndex.set((this.selectedIndex() + delta + count) % count);
  }

  activateSelected(): void {
    if (this.scanRecords.length) {
      this.openRecord(this.scanRecords[this.selectedIndex()] || this.scanRecords[0]);
      return;
    }
    const item = this.filtered()[this.selectedIndex()] || this.filtered()[0];
    if (item) this.run(item);
  }

  run(item: CommandItem): void {
    item.action?.();
    if (item.route) {
      void this.router.navigateByUrl(item.route);
      this.close();
    }
  }

  searchRecord(): void {
    const code = this.query().trim();
    if (!code) return;
    this.scanning = true;
    this.scanner.resolve({ code, module: 'command_palette', action: 'lookup' }).subscribe({
      next: (response) => {
        this.scanning = false;
        this.scanRecords = response.records;
        this.selectedIndex.set(0);
        if (!response.records.length) this.notifications.info(response.message);
      },
      error: (error) => {
        this.scanning = false;
        this.notifications.error(error?.error?.message || 'Lookup failed');
      },
    });
  }

  openRecord(record: ScanResolvedRecord): void {
    if (record.route) {
      void this.router.navigate([record.route], { queryParams: { scan: record.record_id, scanType: record.record_type } });
      this.close();
    }
  }

  private visibleCommands(): CommandItem[] {
    return [...this.menuCommands(menuConfig), ...this.workflowCommands()].filter((item) => this.session.hasPermission(item.permissions));
  }

  private menuCommands(items: MenuItem[], parent = ''): CommandItem[] {
    return items.flatMap((item) => {
      const label = parent ? `${parent} / ${item.label}` : item.label;
      const current = item.route ? [{ label, description: 'Open page', route: item.route, keywords: `${label} ${item.route}`, permissions: item.permissions }] : [];
      return [...current, ...(item.children ? this.menuCommands(item.children, item.label) : [])];
    });
  }

  private workflowCommands(): CommandItem[] {
    return [
      { label: 'Scan barcode or QR', description: 'Open global scanner', route: undefined, keywords: 'scan barcode qr wristband sample invoice', permissions: ['scanner.use'], action: () => document.querySelector<HTMLElement>('.scan-trigger')?.click() },
      { label: 'New invoice', description: 'Billing create flow', route: '/billing/create', keywords: 'bill invoice payment receipt', permissions: ['billing.invoice.create'] },
      { label: 'Collect payment', description: 'Open due payment queue', route: '/billing/due-payments', keywords: 'payment due invoice receipt', permissions: ['billing.payment.collect'] },
      { label: 'Create OPD visit', description: 'Register patient visit', route: '/opd/register', keywords: 'opd visit doctor prescription', permissions: ['opd.visit.create'] },
      { label: 'Admit patient', description: 'Start IPD admission', route: '/ipd/admit', keywords: 'ipd admit bed ward', permissions: ['ipd.admit'] },
      { label: 'Emergency arrival', description: 'Register ER patient', route: '/er/register', keywords: 'emergency triage arrival', permissions: ['er.visit.manage'] },
      { label: 'Lab worklist', description: 'Process samples and results', route: '/laboratory', keywords: 'lab sample result verify', permissions: ['laboratory.view'] },
      { label: 'Radiology worklist', description: 'Process imaging orders', route: '/radiology', keywords: 'radiology imaging report', permissions: ['radiology.view'] },
      { label: 'Pharmacy dispense', description: 'Dispense prescription medicines', route: '/pharmacy/dispense', keywords: 'pharmacy medicine dispense stock', permissions: ['pharmacy.dispense'] },
      { label: 'Inventory transfer', description: 'Open inventory workspace', route: '/inventory', keywords: 'inventory stock receive issue transfer adjust', permissions: ['inventory.view'] },
      { label: 'Blood Bank issue', description: 'Open blood bank workspace', route: '/blood-bank', keywords: 'blood crossmatch issue transfusion unit', permissions: ['blood_bank.view'] },
      { label: 'Shortcut settings', description: 'View keyboard workflow settings', route: '/keyboard/shortcuts', keywords: 'keyboard shortcuts help hotkeys', permissions: ['dashboard.view'] },
    ];
  }
}

