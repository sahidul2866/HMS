import { Injectable, computed, inject, signal } from '@angular/core';

import { ApiCacheService } from './api-cache.service';
import { AppContextService } from './app-context.service';
import { NotificationService } from './notification.service';
import { TabRouteReuseStrategy } from './tab-route-reuse.strategy';

export type AppDataEventName =
  | 'patient.created'
  | 'patient.updated'
  | 'appointment.created'
  | 'appointment.updated'
  | 'appointment.cancelled'
  | 'prescription.created'
  | 'prescription.updated'
  | 'lab.order.created'
  | 'lab.result.verified'
  | 'radiology.report.uploaded'
  | 'billing.invoice.updated'
  | 'billing.payment.received'
  | 'inventory.stock.updated'
  | 'pharmacy.dispense.completed'
  | 'emergency.status.updated'
  | 'ipd.bed.assigned'
  | 'catering.diet_order.created'
  | 'catering.diet_order.approved'
  | 'catering.meal.updated'
  | 'user.permission.updated'
  | 'data.updated';

export interface AppDataEvent {
  name: AppDataEventName;
  entityType: string;
  entityId?: string | null;
  patientId?: string | null;
  visitId?: string | null;
  modules: string[];
  cachePrefixes: string[];
  message: string;
  timestamp: number;
  sourceId: string;
}

@Injectable({ providedIn: 'root' })
export class DataSyncService {
  private static readonly CHANNEL_NAME = 'hms-data-sync';
  private static readonly STORAGE_KEY = 'hms:data-sync:last-event';

  private readonly apiCache = inject(ApiCacheService);
  private readonly notificationService = inject(NotificationService);
  private readonly appContext = inject(AppContextService);
  private readonly routeReuseStrategy = inject(TabRouteReuseStrategy);

  private readonly sourceId = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  private readonly pendingEventsSignal = signal<AppDataEvent[]>([]);
  private channel: BroadcastChannel | null = null;
  private started = false;
  private notifyTimer: ReturnType<typeof setTimeout> | null = null;
  private readonly receivedEventIds = new Set<string>();
  private readonly recentDetailedPublish = new Map<string, number>();

  readonly pendingEvents = this.pendingEventsSignal.asReadonly();
  readonly hasPendingUpdates = computed(() => this.pendingEventsSignal().length > 0);
  readonly pendingMessage = computed(() => {
    const events = this.pendingEventsSignal();
    if (!events.length) return '';
    if (events.length === 1) return events[0].message;
    return `${events.length} related updates are available.`;
  });

  start(): void {
    if (this.started) return;
    this.started = true;
    if ('BroadcastChannel' in window) {
      this.channel = new BroadcastChannel(DataSyncService.CHANNEL_NAME);
      this.channel.onmessage = (message) => this.receive(message.data as AppDataEvent);
    }
    window.addEventListener('storage', (event) => {
      if (event.key !== DataSyncService.STORAGE_KEY || !event.newValue) return;
      try {
        this.receive(JSON.parse(event.newValue) as AppDataEvent);
      } catch {
        // Ignore malformed storage events.
      }
    });
  }

  publish(event: Omit<AppDataEvent, 'timestamp' | 'sourceId'>): void {
    const payload: AppDataEvent = { ...event, timestamp: Date.now(), sourceId: this.sourceId };
    if (event.name !== 'data.updated') {
      for (const module of event.modules) this.recentDetailedPublish.set(module, payload.timestamp);
    }
    this.applyLocalCacheInvalidation(payload);
    window.dispatchEvent(new CustomEvent('hms:data-event', { detail: payload }));
    this.channel?.postMessage(payload);
    try {
      localStorage.setItem(DataSyncService.STORAGE_KEY, JSON.stringify(payload));
    } catch {
      // BroadcastChannel still covers modern browsers; storage can be unavailable.
    }
  }

  publishApiMutation(url: string): void {
    const module = this.moduleFromApiUrl(url);
    if (!module || ['auth', 'patient-auth'].includes(module)) return;
    const now = Date.now();
    if (now - (this.recentDetailedPublish.get(module) ?? 0) < 250) return;

    this.publish({
      name: 'data.updated',
      entityType: module,
      modules: [module, 'dashboard'],
      cachePrefixes: [`${module}:`, 'dashboard:'],
      message: `${module.replace(/-/g, ' ')} data was updated.`,
    });
  }

  prepareApiMutation(url: string): void {
    const module = this.moduleFromApiUrl(url);
    if (!module || ['auth', 'patient-auth'].includes(module)) return;
    this.apiCache.clearPrefix(`${module}:`);
    this.apiCache.clearPrefix('dashboard:');
    this.routeReuseStrategy.invalidateModules([module, 'dashboard']);
  }

  dismiss(event: AppDataEvent): void {
    this.pendingEventsSignal.update((events) => events.filter((item) => item.timestamp !== event.timestamp || item.sourceId !== event.sourceId));
  }

  dismissAll(): void {
    this.pendingEventsSignal.set([]);
  }

  requestRefresh(): void {
    this.dismissAll();
    window.dispatchEvent(new CustomEvent('hms:data-refresh-request', { detail: this.appContext.snapshot() }));
    this.notificationService.info('Latest data is available. Reopen or refresh this panel if it does not update automatically.');
  }

  private receive(event: AppDataEvent): void {
    if (!event || event.sourceId === this.sourceId) return;
    const eventId = `${event.sourceId}:${event.timestamp}`;
    if (this.receivedEventIds.has(eventId)) return;
    this.receivedEventIds.add(eventId);
    if (this.receivedEventIds.size > 100) {
      this.receivedEventIds.delete(this.receivedEventIds.values().next().value!);
    }
    this.applyLocalCacheInvalidation(event);
    window.dispatchEvent(new CustomEvent('hms:data-event', { detail: event }));
    this.requestSoftRefresh(event);
    if (!this.isRelevant(event)) return;
    this.pendingEventsSignal.update((events) => [event, ...events].slice(0, 8));
    this.debouncedNotify();
  }

  private applyLocalCacheInvalidation(event: AppDataEvent): void {
    for (const prefix of event.cachePrefixes || []) {
      this.apiCache.clearPrefix(prefix);
    }
    this.routeReuseStrategy.invalidateModules(event.modules || []);
  }

  private requestSoftRefresh(event: AppDataEvent): void {
    window.dispatchEvent(new CustomEvent('hms:data-refresh-request', { detail: event }));
  }

  private isRelevant(event: AppDataEvent): boolean {
    const context = this.appContext.snapshot();
    if (!event.modules.length) return true;
    if (event.modules.includes(context.activeModule) || event.modules.includes('dashboard')) return true;
    if (event.patientId && event.patientId === context.selectedPatientId) return true;
    if (event.visitId && event.visitId === context.selectedVisitId) return true;
    return false;
  }

  private debouncedNotify(): void {
    if (this.notifyTimer) window.clearTimeout(this.notifyTimer);
    this.notifyTimer = window.setTimeout(() => {
      const hasDirtyForm = !!document.querySelector('form.ng-dirty, form.app-form-submitted');
      const message = hasDirtyForm ? 'This page has newer data. Your draft was not overwritten.' : this.pendingMessage();
      this.notificationService.info(message || 'Updated data is available.');
    }, 350);
  }

  private moduleFromApiUrl(url: string): string | null {
    const path = new URL(url, window.location.origin).pathname;
    const segments = path.split('/').filter(Boolean);
    const apiIndex = segments.findIndex((segment) => segment === 'v1');
    return segments[apiIndex >= 0 ? apiIndex + 1 : 0] ?? null;
  }
}
