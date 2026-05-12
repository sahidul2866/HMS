import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiBaseService } from '../../../core/services/api-base.service';
import { ScanCode, ScanResolveRequest, ScanResolveResponse, ScanSetting } from '../models/scanner.models';

@Injectable({ providedIn: 'root' })
export class ScannerService extends ApiBaseService {
  resolve(payload: ScanResolveRequest): Observable<ScanResolveResponse> {
    return this.http.post<ScanResolveResponse>(this.url('/scanner/resolve'), payload);
  }

  generateCode(payload: { record_type: string; record_id: string; purpose: string; code_type?: string; display_value?: string }): Observable<ScanCode> {
    return this.http.post<ScanCode>(this.url('/scanner/codes'), payload);
  }

  listSettings(): Observable<ScanSetting[]> {
    return this.http.get<ScanSetting[]>(this.url('/scanner/settings'));
  }

  saveSetting(payload: { setting_key: string; setting_value: Record<string, unknown>; department_id?: string | null }): Observable<ScanSetting> {
    return this.http.post<ScanSetting>(this.url('/scanner/settings'), payload);
  }
}

