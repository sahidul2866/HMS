import { Injectable } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class ActionConfirmationService {
  confirmDestructive(itemLabel: string, action = 'delete'): boolean {
    return window.confirm(`Confirm ${action}: ${itemLabel}\n\nThis action cannot be undone.`);
  }

  confirmImportant(message: string): boolean {
    return window.confirm(message);
  }
}
