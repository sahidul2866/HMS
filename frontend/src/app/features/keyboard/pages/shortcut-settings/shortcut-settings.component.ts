import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';

interface ShortcutGroup {
  title: string;
  shortcuts: Array<{ keys: string; action: string; safety?: string }>;
}

@Component({
  selector: 'app-shortcut-settings',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './shortcut-settings.component.html',
  styleUrls: ['./shortcut-settings.component.scss'],
})
export class ShortcutSettingsComponent {
  readonly groups: ShortcutGroup[] = [
    {
      title: 'Global',
      shortcuts: [
        { keys: 'Ctrl/Cmd+K', action: 'Open command palette' },
        { keys: 'Alt+B', action: 'Open barcode/QR scanner' },
        { keys: '? or Ctrl/Cmd+/', action: 'Open shortcut help' },
        { keys: 'Alt+1...7', action: 'Jump to dashboard, patients, OPD, billing, pharmacy, lab, radiology' },
        { keys: 'Alt+[ / Alt+]', action: 'Move between open tabs' },
        { keys: 'Alt+S', action: 'Toggle sidebar' },
        { keys: 'Alt+M', action: 'Cycle page density' },
      ],
    },
    {
      title: 'Forms',
      shortcuts: [
        { keys: 'Tab / Shift+Tab', action: 'Move forward/backward through fields' },
        { keys: 'Enter', action: 'Move to next field or submit final safe action' },
        { keys: 'Ctrl/Cmd+S', action: 'Save focused form' },
        { keys: 'Esc', action: 'Close temporary UI or clear focus' },
      ],
    },
    {
      title: 'Tables and Search',
      shortcuts: [
        { keys: 'Arrow Up/Down', action: 'Move focused table row or palette result' },
        { keys: 'Enter', action: 'Open focused result/action' },
        { keys: 'Alt+/', action: 'Focus first search/filter on current page' },
      ],
    },
    {
      title: 'Safety',
      shortcuts: [
        { keys: 'Enter', action: 'Blocked for destructive actions', safety: 'Delete, cancel, refund, final discharge, payroll approval, stock adjustment, blood override, and reset actions require explicit confirmation.' },
        { keys: 'Repeat Enter', action: 'Duplicate submit protection', safety: 'Forms ignore repeated submits for a short guard window while the API request starts.' },
      ],
    },
  ];
}

