import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiBaseService } from './api-base.service';

export interface HmsNotification {
  id: string;
  title: string;
  message: string;
  category: string;
  module: string;
  priority: 'critical' | 'high' | 'medium' | 'low' | 'informational' | string;
  status: 'unread' | 'read' | 'action_required' | 'in_progress' | 'completed' | 'dismissed' | 'escalated' | 'expired' | string;
  notification_type: string;
  related_record_type?: string | null;
  related_record_id?: string | null;
  related_display?: string | null;
  route?: string | null;
  action_label?: string | null;
  action_permission?: string | null;
  due_at?: string | null;
  read_at?: string | null;
  completed_at?: string | null;
  dismissed_at?: string | null;
  escalated_at?: string | null;
  created_at: string;
  meta?: Record<string, unknown>;
  action_allowed: boolean;
  overdue: boolean;
}

export interface NotificationSummary {
  unread_count: number;
  action_required_count: number;
  critical_count: number;
  latest: HmsNotification[];
}

export interface NotificationListResponse extends NotificationSummary {
  items: HmsNotification[];
  total: number;
}

export interface NotificationSetting {
  id: string;
  setting_key: string;
  setting_value: Record<string, unknown>;
}

@Injectable({ providedIn: 'root' })
export class HmsNotificationService extends ApiBaseService {
  summary(): Observable<NotificationSummary> {
    return this.http.get<NotificationSummary>(this.url('/notifications/summary'));
  }

  list(params: Record<string, string | number | boolean | null | undefined> = {}): Observable<NotificationListResponse> {
    const clean: Record<string, string | number | boolean> = {};
    Object.entries(params).forEach(([key, value]) => {
      if (value !== null && value !== undefined && value !== '') clean[key] = value;
    });
    return this.http.get<NotificationListResponse>(this.url('/notifications'), { params: clean as any });
  }

  updateStatus(id: string, status: 'read' | 'dismissed' | 'completed' | 'in_progress'): Observable<HmsNotification> {
    return this.http.post<HmsNotification>(this.url(`/notifications/${id}/status`), { status });
  }

  markAllRead(): Observable<{ updated: number }> {
    return this.http.post<{ updated: number }>(this.url('/notifications/mark-all-read'), {});
  }

  listSettings(): Observable<NotificationSetting[]> {
    return this.http.get<NotificationSetting[]>(this.url('/notifications/settings'));
  }

  saveSetting(payload: { setting_key: string; setting_value: Record<string, unknown> }): Observable<NotificationSetting> {
    return this.http.post<NotificationSetting>(this.url('/notifications/settings'), payload);
  }
}
