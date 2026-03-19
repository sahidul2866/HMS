import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';

import { NotificationService } from '../services/notification.service';

export const errorInterceptor: HttpInterceptorFn = (request, next) => {
  const notificationService = inject(NotificationService);

  return next(request).pipe(
    catchError((error: unknown) => {
      if (error instanceof HttpErrorResponse) {
        const normalized = {
          status: error.status,
          code: error.error?.error?.code ?? 'http_error',
          message: error.error?.error?.message ?? error.message,
          details: error.error?.error?.details ?? null,
        };
        notificationService.error(normalized.message);
        return throwError(() => normalized);
      }
      return throwError(() => error);
    })
  );
};
