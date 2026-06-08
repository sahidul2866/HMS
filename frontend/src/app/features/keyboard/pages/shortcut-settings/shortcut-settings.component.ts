import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';

import { RoleExperienceService } from '../../../../core/services/role-experience.service';
import { SessionService } from '../../../../core/services/session.service';

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
  private readonly roleExperience = inject(RoleExperienceService);
  private readonly session = inject(SessionService);

  get roleTitle(): string {
    return `${this.roleExperience.primaryExperience().label} User Manual`;
  }

  get roleFocus(): string[] {
    return this.roleExperience.primaryExperience().focus;
  }

  get roleActions(): Array<{ label: string; detail: string; shortcut?: string }> {
    return this.roleExperience.visibleActions().map((action) => ({
      label: action.label,
      detail: action.detail,
      shortcut: action.shortcut,
    }));
  }

  get roleShortcuts(): Array<{ keys: string; action: string }> {
    return this.roleExperience.visibleShortcuts().map((shortcut) => ({
      keys: shortcut.key,
      action: shortcut.label,
    }));
  }

  get userName(): string {
    return this.session.snapshot.user?.full_name || 'Current user';
  }

  readonly groups: ShortcutGroup[] = [
    {
      title: 'Global',
      shortcuts: [
        { keys: 'Ctrl/Cmd+K', action: 'Open command palette' },
        { keys: 'Alt+B', action: 'Open barcode/QR scanner' },
        { keys: '? or Ctrl/Cmd+/', action: 'Open this user manual' },
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
