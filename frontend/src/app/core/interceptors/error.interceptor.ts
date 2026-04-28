import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';

import { NotificationService } from '../services/notification.service';

export const errorInterceptor: HttpInterceptorFn = (request, next) => {
  const notificationService = inject(NotificationService);

  return next(request).pipe(
    catchError((error: unknown) => {
      if (error instanceof HttpErrorResponse) {
        if (error.status === 0) {
          const normalized = {
            status: 0,
            code: 'api_unreachable',
            message: 'API server is unreachable. Check that the backend is running and try again.',
            details: null,
          };
          notificationService.error(normalized.message);
          return throwError(() => normalized);
        }

        const normalized = {
          status: error.status,
          code: error.error?.error?.code ?? 'http_error',
          message: error.error?.error?.message ?? error.message,
          details: error.error?.error?.request_id
            ? { request_id: error.error.error.request_id, details: error.error?.error?.details ?? null }
            : error.error?.error?.details ?? null,
        };
        const isSilentUnauthorizedBootstrap = request.url.endsWith('/auth/me') && normalized.status === 401;
        if (!isSilentUnauthorizedBootstrap) {
          notificationService.error(normalized.message);
        }
        return throwError(() => normalized);
      }
      return throwError(() => error);
    })
  );
};
