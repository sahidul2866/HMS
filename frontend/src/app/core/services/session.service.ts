import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

import { SessionState, User } from '../models/auth.models';

@Injectable({ providedIn: 'root' })
export class SessionService {
  private static readonly LANDING_PRIORITY: Array<{ permission: string; route: string }> = [
    { permission: 'dashboard.view', route: '/dashboard' },
    { permission: 'opd.view', route: '/opd' },
    { permission: 'appointment.view', route: '/appointments' },
    { permission: 'ipd.view', route: '/ipd' },
    { permission: 'billing.view', route: '/billing' },
    { permission: 'patient.view', route: '/patients' },
    { permission: 'laboratory.view', route: '/laboratory' },
    { permission: 'radiology.view', route: '/radiology' },
    { permission: 'pharmacy.view', route: '/pharmacy' },
    { permission: 'inventory.view', route: '/inventory' },
    { permission: 'er.view', route: '/er' },
    { permission: 'ot.view', route: '/ot' },
    { permission: 'hr.view', route: '/hr' },
    { permission: 'accounting.view', route: '/accounting' },
    { permission: 'reporting.view', route: '/reporting' },
  ];

  private readonly stateSubject = new BehaviorSubject<SessionState>({
    initialized: false,
    authenticated: false,
    user: null,
  });

  readonly state$ = this.stateSubject.asObservable();

  get snapshot(): SessionState {
    return this.stateSubject.value;
  }

  initialize(user: User | null): void {
    this.stateSubject.next({
      initialized: true,
      authenticated: !!user,
      user,
    });
  }

  setAnonymous(): void {
    this.initialize(null);
  }

  setUser(user: User): void {
    this.stateSubject.next({
      initialized: true,
      authenticated: true,
      user,
    });
  }

  clear(): void {
    this.setAnonymous();
  }

  hasPermission(permission: string | string[]): boolean {
    const userPermissions = new Set(this.snapshot.user?.effective_permissions ?? []);
    const required = Array.isArray(permission) ? permission : [permission];
    return required.every((item) => userPermissions.has(item));
  }

  hasAnyPermission(permission: string | string[]): boolean {
    const userPermissions = new Set(this.snapshot.user?.effective_permissions ?? []);
    const required = Array.isArray(permission) ? permission : [permission];
    return required.some((item) => userPermissions.has(item));
  }

  getLandingRoute(): string {
    const user = this.snapshot.user;
    if (!user) {
      return '/auth/login';
    }
    if (user.effective_permissions.includes('patient.portal.view') && !!user.patient_id) {
      return '/portal';
    }
    for (const candidate of SessionService.LANDING_PRIORITY) {
      if (user.effective_permissions.includes(candidate.permission)) {
        return candidate.route;
      }
    }
    return '/profile';
  }
}
