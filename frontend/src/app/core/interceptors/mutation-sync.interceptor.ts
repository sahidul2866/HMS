import { HttpEventType, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { tap } from 'rxjs';

import { DataSyncService } from '../services/data-sync.service';

const MUTATION_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);

export const mutationSyncInterceptor: HttpInterceptorFn = (request, next) => {
  const dataSync = inject(DataSyncService);
  if (!MUTATION_METHODS.has(request.method.toUpperCase())) {
    return next(request);
  }

  return next(request).pipe(
    tap((event) => {
      if (event.type !== HttpEventType.Response) return;
      dataSync.prepareApiMutation(request.url);
      queueMicrotask(() => dataSync.publishApiMutation(request.url));
    })
  );
};
