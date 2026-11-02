import { inject } from '@angular/core';
import { ActivatedRouteSnapshot, CanActivateFn, Router } from '@angular/router';

import { NotificationService } from '../services/notification.service';
import { SessionService } from '../services/session.service';

export const permissionGuard: CanActivateFn = (route: ActivatedRouteSnapshot) => {
  const sessionService = inject(SessionService);
  const router = inject(Router);
  const notifications = inject(NotificationService);
  const permissions = route.data['permissions'] as string[] | undefined;

  if (!sessionService.snapshot.authenticated) {
    return router.createUrlTree(['/auth/login']);
  }

  if (!permissions?.length) {
    return true;
  }

  if (route.data['permissionMode'] === 'any' ? sessionService.hasAnyPermission(permissions) : sessionService.hasPermission(permissions)) {
    return true;
  }
  notifications.warning('This section requires additional permission. Ask your administrator for access. You can continue using the sections available from your profile.');
  return router.createUrlTree([sessionService.snapshot.authenticated ? '/profile' : '/auth/login']);
};
