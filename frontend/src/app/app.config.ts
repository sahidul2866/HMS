import { APP_INITIALIZER, ApplicationConfig, provideZoneChangeDetection } from '@angular/core';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideRouter, RouteReuseStrategy, withHashLocation, withRouterConfig } from '@angular/router';

import { appRoutes } from './app.routes';
import { authInterceptor } from './core/interceptors/auth.interceptor';
import { errorInterceptor } from './core/interceptors/error.interceptor';
import { loadingInterceptor } from './core/interceptors/loading.interceptor';
import { mutationSyncInterceptor } from './core/interceptors/mutation-sync.interceptor';
import { AuthService } from './core/services/auth.service';
import { DataSyncService } from './core/services/data-sync.service';
import { GlobalFormValidationService } from './core/services/global-form-validation.service';
import { GlobalSmartInputService } from './core/services/global-smart-input.service';
import { KeyboardWorkflowService } from './core/services/keyboard-workflow.service';
import { TabRouteReuseStrategy } from './core/services/tab-route-reuse.strategy';

function bootstrapSession(authService: AuthService) {
  return () => authService.bootstrapSession();
}

function bootstrapFormValidation(validationService: GlobalFormValidationService) {
  return () => validationService.start();
}

function bootstrapSmartInputs(smartInputService: GlobalSmartInputService) {
  return () => smartInputService.start();
}

function bootstrapDataSync(dataSyncService: DataSyncService) {
  return () => dataSyncService.start();
}

function bootstrapKeyboardWorkflow(keyboardWorkflowService: KeyboardWorkflowService) {
  return () => keyboardWorkflowService.start();
}

export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(appRoutes, withHashLocation(), withRouterConfig({ onSameUrlNavigation: 'reload' })),
    provideHttpClient(withInterceptors([loadingInterceptor, errorInterceptor, authInterceptor, mutationSyncInterceptor])),
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
    {
      provide: APP_INITIALIZER,
      multi: true,
      deps: [GlobalFormValidationService],
      useFactory: bootstrapFormValidation,
    },
    {
      provide: APP_INITIALIZER,
      multi: true,
      deps: [GlobalSmartInputService],
      useFactory: bootstrapSmartInputs,
    },
    {
      provide: APP_INITIALIZER,
      multi: true,
      deps: [DataSyncService],
      useFactory: bootstrapDataSync,
    },
    {
      provide: APP_INITIALIZER,
      multi: true,
      deps: [KeyboardWorkflowService],
      useFactory: bootstrapKeyboardWorkflow,
    },
  ],
};
