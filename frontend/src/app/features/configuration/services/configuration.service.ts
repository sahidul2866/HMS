import { Injectable, inject } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { ApiBaseService } from '../../../core/services/api-base.service';
import { ApiCacheService } from '../../../core/services/api-cache.service';

export interface ConfigurationProfile {
  id: string;
  branch_id?: string | null;
  profile_type: string;
  code: string;
  name: string;
  description?: string | null;
  scope: string;
  target_type?: string | null;
  target_id?: string | null;
  payload: Record<string, unknown>;
  is_default: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ConfigurationWorkspace {
  profiles: ConfigurationProfile[];
  counts: Record<string, number>;
  demo_points: string[];
}

@Injectable({ providedIn: 'root' })
export class ConfigurationService extends ApiBaseService {
  private readonly cache = inject(ApiCacheService);

  workspace(): Observable<ConfigurationWorkspace> {
    return this.cache.get('configuration:workspace', () => this.http.get<ConfigurationWorkspace>(this.url('/configuration/workspace')));
  }

  list(profileType?: string): Observable<ConfigurationProfile[]> {
    const query = profileType ? `?profile_type=${encodeURIComponent(profileType)}` : '';
    return this.cache.get(`configuration:profiles:${profileType || 'all'}`, () => this.http.get<ConfigurationProfile[]>(this.url(`/configuration/profiles${query}`)));
  }

  create(payload: Record<string, unknown>): Observable<ConfigurationProfile> {
    return this.http.post<ConfigurationProfile>(this.url('/configuration/profiles'), payload).pipe(tap(() => this.clear()));
  }

  update(id: string, payload: Record<string, unknown>): Observable<ConfigurationProfile> {
    return this.http.put<ConfigurationProfile>(this.url(`/configuration/profiles/${id}`), payload).pipe(tap(() => this.clear()));
  }

  delete(id: string): Observable<{ success: boolean }> {
    return this.http.delete<{ success: boolean }>(this.url(`/configuration/profiles/${id}`)).pipe(tap(() => this.clear()));
  }

  clear(): void {
    this.cache.clearPrefix('configuration:');
    this.cache.clearPrefix('billing:settings');
  }
}
