import { APP_INITIALIZER, ApplicationConfig, provideZoneChangeDetection } from '@angular/core';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideRouter, RouteReuseStrategy, withHashLocation } from '@angular/router';

import { appRoutes } from './app.routes';
import { authInterceptor } from './core/interceptors/auth.interceptor';
import { errorInterceptor } from './core/interceptors/error.interceptor';
import { loadingInterceptor } from './core/interceptors/loading.interceptor';
import { AuthService } from './core/services/auth.service';
import { TabRouteReuseStrategy } from './core/services/tab-route-reuse.strategy';

function bootstrapSession(authService: AuthService) {
  return () => authService.bootstrapSession();
}

export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(appRoutes, withHashLocation()),
    provideHttpClient(withInterceptors([loadingInterceptor, errorInterceptor, authInterceptor])),
    TabRouteReuseStrategy,
    {
      provide: RouteReuseStrategy,
      useExisting: TabRouteReuseStrategy,
    },
    {
      provide: APP_INITIALIZER,
      multi: true,
      deps: [AuthService],
      useFactory: bootstrapSession,
    },
  ],
};
