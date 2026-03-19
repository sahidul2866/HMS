import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { catchError, throwError } from 'rxjs';

export const errorInterceptor: HttpInterceptorFn = (request, next) =>
  next(request).pipe(
    catchError((error: unknown) => {
      if (error instanceof HttpErrorResponse) {
        const normalized = {
          status: error.status,
          code: error.error?.error?.code ?? 'http_error',
          message: error.error?.error?.message ?? error.message,
          details: error.error?.error?.details ?? null,
        };
        return throwError(() => normalized);
      }
      return throwError(() => error);
    })
  );

