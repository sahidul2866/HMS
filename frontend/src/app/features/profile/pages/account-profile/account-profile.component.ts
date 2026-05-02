import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { Router } from '@angular/router';

import { AuthService } from '../../../../core/services/auth.service';
import { NotificationService } from '../../../../core/services/notification.service';
import { SessionService } from '../../../../core/services/session.service';

@Component({
  selector: 'app-account-profile',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './account-profile.component.html',
  styleUrl: './account-profile.component.scss',
})
export class AccountProfileComponent {
  readonly session = inject(SessionService);
  private readonly auth = inject(AuthService);
  private readonly notification = inject(NotificationService);
  private readonly router = inject(Router);

  get user() {
    return this.session.snapshot.user;
  }

  initials(): string {
    const name = this.user?.full_name || 'User';
    return name
      .split(' ')
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0]?.toUpperCase())
      .join('');
  }

  accountType(): string {
    if (this.user?.principal_type === 'patient' || this.user?.patient_id) {
      return 'Patient Portal Account';
    }
    return 'Staff Account';
  }

  primaryRole(): string {
    if (this.user?.principal_type === 'patient') {
      return 'Patient';
    }
    return this.user?.roles?.[0]?.name || 'No role assigned';
  }

  permissionGroups(): Array<{ label: string; count: number }> {
    const grouped = new Map<string, number>();
    for (const permission of this.user?.effective_permissions || []) {
      const module = permission.split('.')[0] || 'general';
      grouped.set(module, (grouped.get(module) || 0) + 1);
    }
    return Array.from(grouped.entries())
      .map(([label, count]) => ({ label, count }))
      .sort((a, b) => a.label.localeCompare(b.label));
  }

  goPortal(): void {
    void this.router.navigateByUrl('/portal');
  }

  goDashboard(): void {
    void this.router.navigateByUrl('/dashboard');
  }

  logout(): void {
    this.auth.logout().subscribe(() => this.notification.info('Logged out.'));
  }
}
