import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';

import { SKIP_ERROR_NOTIFICATION } from '../http/http-context.tokens';
import { NotificationService } from '../services/notification.service';

export const errorInterceptor: HttpInterceptorFn = (request, next) => {
  const notificationService = inject(NotificationService);

  return next(request).pipe(
    catchError((error: unknown) => {
      if (request.context.get(SKIP_ERROR_NOTIFICATION)) return throwError(() => error);
      if (error instanceof HttpErrorResponse) {
        if (error.status === 0) {
          const normalized = {
            status: 0,
            code: 'api_unreachable',
            message: navigator.onLine ? 'The server could not be reached. Keep your form open, check your connection, and try again. If you submitted a payment or record, check its status before resubmitting.' : 'You’re offline. Loaded information is still available. Reconnect to search or save; your changes have not been sent.',
            details: null,
          };
          notificationService.error(normalized.message);
          return throwError(() => normalized);
        }

        const normalized = {
          status: error.status,
          code: error.error?.error?.code ?? 'http_error',
          message: error.status === 403
            ? 'Your account does not have permission for this action. Ask an administrator for access, or return to a section available to your role.'
            : error.status >= 500
              ? 'The server could not complete this request. Keep your form open and try again shortly. Check whether your change was saved before submitting again.'
              : error.status === 429
                ? 'Too many requests. Wait a moment, then try again.'
                : error.error?.error?.message ?? 'The request could not be completed. Check your entries and try again.',
          details: error.error?.error?.request_id
            ? { request_id: error.error.error.request_id, details: error.error?.error?.details ?? null }
            : error.error?.error?.details ?? null,
        };
        const isSilentUnauthorizedBootstrap = request.url.endsWith('/auth/me') && normalized.status === 401;
        // A page the role may open often also reads lookup data the role has no right to (for example a doctor list or a
        // report widget). That read fails quietly and the page shows what the role can see; mutations and scope
        // restrictions that carry their own explanation still tell the user.
        const serverMessage: string = error.error?.error?.message ?? '';
        const isPermissionGate = /^(Missing permissions|Requires any of)/.test(serverMessage);
        const isQuietForbiddenRead = request.method === 'GET' && error.status === 403 && isPermissionGate;
        if (error.status === 403 && serverMessage && !isPermissionGate) normalized.message = serverMessage;
        if (!isSilentUnauthorizedBootstrap && !isQuietForbiddenRead) {
          notificationService.error(normalized.message);
        }
        return throwError(() => normalized);
      }
      return throwError(() => error);
    })
  );
};
