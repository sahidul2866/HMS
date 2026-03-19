import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

import { SessionState, User } from '../models/auth.models';

@Injectable({ providedIn: 'root' })
export class SessionService {
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
}
