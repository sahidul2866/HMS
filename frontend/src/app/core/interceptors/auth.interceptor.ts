import { HttpErrorResponse, HttpEvent, HttpHandlerFn, HttpInterceptorFn, HttpRequest } from '@angular/common/http';
import { inject } from '@angular/core';
import { Observable, catchError, throwError } from 'rxjs';

import { AuthService } from '../services/auth.service';
import { TokenStorageService } from '../services/token-storage.service';

export const authInterceptor: HttpInterceptorFn = (request: HttpRequest<unknown>, next: HttpHandlerFn): Observable<HttpEvent<unknown>> => {
  const tokenStorage = inject(TokenStorageService);
  const authService = inject(AuthService);
  const accessToken = tokenStorage.getAccessToken();
  const shouldAttachAccessToken = !request.headers.has('X-Skip-Auth-Refresh')
    && !request.url.endsWith('/auth/refresh')
    && !request.url.endsWith('/patient-auth/refresh')
    && !request.url.endsWith('/patient-auth/register')
    && !request.url.endsWith('/patient-auth/patients/search');

  const authRequest = accessToken && shouldAttachAccessToken
    ? request.clone({
        setHeaders: {
          Authorization: `Bearer ${accessToken}`,
        },
      })
    : request;

  return next(authRequest).pipe(
    catchError((error: unknown) => {
      if (error instanceof HttpErrorResponse && error.status === 401) {
        return authService.handleUnauthorized(authRequest, next) as Observable<HttpEvent<unknown>>;
      }
      return throwError(() => error);
    })
  );
};
