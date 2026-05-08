import { Injectable, computed, inject, signal } from '@angular/core';
import { NavigationEnd, Router } from '@angular/router';
import { filter } from 'rxjs';

import { SessionService } from './session.service';

export interface AppContextSnapshot {
  currentUserId: string | null;
  branchId: string | null;
  permissions: string[];
  activeRoute: string;
  activeModule: string;
  selectedPatientId: string | null;
  selectedVisitId: string | null;
  selectedAdmissionId: string | null;
  selectedEmergencyId: string | null;
}

@Injectable({ providedIn: 'root' })
export class AppContextService {
  private readonly router = inject(Router);
  private readonly session = inject(SessionService);

  private readonly activeRouteSignal = signal('');
  private readonly selectedPatientIdSignal = signal<string | null>(null);
  private readonly selectedVisitIdSignal = signal<string | null>(null);
  private readonly selectedAdmissionIdSignal = signal<string | null>(null);
  private readonly selectedEmergencyIdSignal = signal<string | null>(null);

  readonly snapshot = computed<AppContextSnapshot>(() => {
    const user = this.session.snapshot.user;
    const activeRoute = this.activeRouteSignal();
    return {
      currentUserId: user?.id || null,
      branchId: user?.branch_id || null,
      permissions: user?.effective_permissions || [],
      activeRoute,
      activeModule: this.moduleFromRoute(activeRoute),
      selectedPatientId: this.selectedPatientIdSignal(),
      selectedVisitId: this.selectedVisitIdSignal(),
      selectedAdmissionId: this.selectedAdmissionIdSignal(),
      selectedEmergencyId: this.selectedEmergencyIdSignal(),
    };
  });

  constructor() {
    this.activeRouteSignal.set(this.router.url);
    this.router.events.pipe(filter((event): event is NavigationEnd => event instanceof NavigationEnd)).subscribe((event) => {
      this.activeRouteSignal.set(event.urlAfterRedirects);
    });
  }

  setSelectedPatient(patientId: string | null): void {
    this.selectedPatientIdSignal.set(patientId);
  }

  setSelectedVisit(visitId: string | null): void {
    this.selectedVisitIdSignal.set(visitId);
  }

  setSelectedAdmission(admissionId: string | null): void {
    this.selectedAdmissionIdSignal.set(admissionId);
  }

  setSelectedEmergencyCase(emergencyId: string | null): void {
    this.selectedEmergencyIdSignal.set(emergencyId);
  }

  private moduleFromRoute(route: string): string {
    const clean = route.split('?')[0].split('#')[0];
    return clean.split('/').filter(Boolean)[0] || 'dashboard';
  }
}
