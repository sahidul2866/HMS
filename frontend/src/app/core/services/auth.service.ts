import { HttpClient, HttpEvent, HttpRequest } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, catchError, finalize, firstValueFrom, map, of, shareReplay, switchMap, tap, throwError } from 'rxjs';

import { ApiError, LoginResponse, TokenPair, User } from '../models/auth.models';
import { runtimeConfig } from '../config/runtime-config';
import { SessionService } from './session.service';
import { TabService } from './tab.service';
import { TokenStorageService } from './token-storage.service';
import { CurrentUserService } from './current-user.service';
import { UiStateService } from './ui-state.service';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private static readonly SKIP_AUTH_REFRESH_HEADER = 'X-Skip-Auth-Refresh';
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  private readonly sessionService = inject(SessionService);
  private readonly tokenStorage = inject(TokenStorageService);
  private readonly currentUserService = inject(CurrentUserService);
  private readonly tabService = inject(TabService);
  private readonly uiStateService = inject(UiStateService);
  private refreshInFlight$: Observable<LoginResponse> | null = null;

  async bootstrapSession(): Promise<void> {
    const accessToken = this.tokenStorage.getAccessToken();
    const refreshToken = this.tokenStorage.getRefreshToken();

    if (!accessToken && !refreshToken) {
      this.sessionService.setAnonymous();
      await this.redirectToLoginIfNeeded();
      return;
    }

    try {
      const user = await firstValueFrom(this.currentUserService.getCurrentUser());
      this.sessionService.initialize(user);
    } catch {
      if (!refreshToken) {
        this.clearSession();
        await this.redirectToLoginIfNeeded();
        return;
      }

      try {
        const result = await firstValueFrom(this.refreshAccessToken());
        this.persistTokens(result.tokens);
        this.sessionService.initialize(result.user);
      } catch {
        this.clearSession();
        await this.redirectToLoginIfNeeded();
      }
    }
  }

  login(username_or_email: string, password: string): Observable<User> {
    return this.http
      .post<LoginResponse>(`${runtimeConfig.apiBaseUrl}/auth/login`, { username_or_email, password }, {
        headers: {
          [AuthService.SKIP_AUTH_REFRESH_HEADER]: '1',
        },
      })
      .pipe(
        tap((response) => {
          this.persistTokens(response.tokens);
          this.sessionService.setUser(response.user);
        }),
        map((response) => response.user)
      );
  }

  registerPatient(payload: {
    username: string;
    email: string;
    full_name: string;
    password: string;
    phone?: string | null;
    gender?: string | null;
    date_of_birth?: string | null;
    address?: string | null;
    emergency_contact_name?: string | null;
    emergency_contact_phone?: string | null;
  }): Observable<User> {
    return this.http
      .post<LoginResponse>(`${runtimeConfig.apiBaseUrl}/auth/patient-register`, payload, {
        headers: {
          [AuthService.SKIP_AUTH_REFRESH_HEADER]: '1',
        },
      })
      .pipe(
        tap((response) => {
          this.persistTokens(response.tokens);
          this.sessionService.setUser(response.user);
        }),
        map((response) => response.user)
      );
  }

  refreshAccessToken(): Observable<LoginResponse> {
    if (this.refreshInFlight$) {
      return this.refreshInFlight$;
    }

    const refreshToken = this.tokenStorage.getRefreshToken();
    if (!refreshToken) {
      return throwError(() => ({ status: 401, code: 'missing_refresh_token', message: 'No refresh token available' } as ApiError));
    }

    this.refreshInFlight$ = this.http
      .post<LoginResponse>(
        `${runtimeConfig.apiBaseUrl}/auth/refresh`,
        { refresh_token: refreshToken },
        {
          headers: {
            [AuthService.SKIP_AUTH_REFRESH_HEADER]: '1',
          },
        }
      )
      .pipe(
        tap((response) => {
          this.persistTokens(response.tokens);
          this.sessionService.setUser(response.user);
        }),
        finalize(() => {
          this.refreshInFlight$ = null;
        }),
        shareReplay(1)
      );

    return this.refreshInFlight$;
  }

  handleUnauthorized(
    request: HttpRequest<unknown>,
    next: (request: HttpRequest<unknown>) => Observable<HttpEvent<unknown>>,
  ): Observable<HttpEvent<unknown>> {
    if (
      request.url.endsWith('/auth/login')
      || request.url.endsWith('/auth/refresh')
      || request.headers.has('X-Retry-Attempt')
      || request.headers.has(AuthService.SKIP_AUTH_REFRESH_HEADER)
    ) {
      this.clearSession(true);
      return throwError(() => ({ status: 401, code: 'unauthorized', message: 'Authentication failed' } as ApiError));
    }

    return this.refreshAccessToken().pipe(
      switchMap((response) => {
        const retried = request.clone({
          setHeaders: {
            Authorization: `Bearer ${response.tokens.access_token}`,
            'X-Retry-Attempt': '1',
          },
        });
        return next(retried);
      }),
      catchError((error) => {
        this.clearSession(true);
        return throwError(() => error);
      })
    );
  }

  logout(): Observable<void> {
    const refreshToken = this.tokenStorage.getRefreshToken();
    if (!refreshToken) {
      this.clearSession(true);
      return of(void 0);
    }

    return this.http.post<void>(
      `${runtimeConfig.apiBaseUrl}/auth/logout`,
      { refresh_token: refreshToken },
      {
        headers: {
          [AuthService.SKIP_AUTH_REFRESH_HEADER]: '1',
        },
      }
    ).pipe(
      catchError(() => of(void 0)),
      tap(() => this.clearSession(true))
    );
  }

  clearSession(navigate = false): void {
    this.tokenStorage.clear();
    this.sessionService.clear();
    this.tabService.clear();
    this.uiStateService.clearAll();
    if (navigate) {
      void this.router.navigate(['/auth/login']);
    }
  }

  private async redirectToLoginIfNeeded(): Promise<void> {
    if (this.router.url.startsWith('/auth/login')) {
      return;
    }
    await this.router.navigate(['/auth/login']);
  }

  private persistTokens(tokens: TokenPair): void {
    this.tokenStorage.setTokens(tokens.access_token, tokens.refresh_token);
  }

  getLandingRoute(user: User): string {
    return user.effective_permissions.includes('patient.portal.view') ? '/portal' : '/dashboard';
  }
}
