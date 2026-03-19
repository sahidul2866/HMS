import { inject } from '@angular/core';
import { ActivatedRouteSnapshot, CanActivateFn, Router } from '@angular/router';

import { SessionService } from '../services/session.service';

export const permissionGuard: CanActivateFn = (route: ActivatedRouteSnapshot) => {
  const sessionService = inject(SessionService);
  const router = inject(Router);
  const permissions = route.data['permissions'] as string[] | undefined;

  if (!sessionService.snapshot.authenticated) {
    return router.createUrlTree(['/auth/login']);
  }

  if (!permissions?.length) {
    return true;
  }

  return sessionService.hasPermission(permissions) ? true : router.createUrlTree(['/dashboard']);
};
