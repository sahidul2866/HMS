import { Injectable } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { ApiCacheService } from '../../../core/services/api-cache.service';
import { ApiBaseService } from '../../../core/services/api-base.service';
import { LISMachine, LISQueueItem, LISSimulationRequest, LISSimulationResult } from '../models/lis.models';

@Injectable({ providedIn: 'root' })
export class LISServiceApi extends ApiBaseService {
  constructor(private readonly cache: ApiCacheService) {
    super();
  }

  listMachines(): Observable<LISMachine[]> {
    return this.cache.get('lis:machines', () => this.http.get<LISMachine[]>(this.url('/lis/machines')));
  }

  listQueue(): Observable<LISQueueItem[]> {
    return this.cache.get('lis:queue', () => this.http.get<LISQueueItem[]>(this.url('/lis/queue')));
  }

  simulateAnalyze(payload: LISSimulationRequest): Observable<LISSimulationResult> {
    return this.http.post<LISSimulationResult>(this.url('/lis/simulate-analyze'), payload).pipe(
      tap(() => {
        this.cache.clearPrefix('lis:');
        this.cache.clearPrefix('laboratory:');
      })
    );
  }
}
