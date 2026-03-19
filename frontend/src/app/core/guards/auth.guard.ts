import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { SessionService } from '../services/session.service';

export const authGuard: CanActivateFn = () => {
  const sessionService = inject(SessionService);
  const router = inject(Router);

  if (!sessionService.snapshot.initialized) {
    return false;
  }

  return sessionService.snapshot.authenticated ? true : router.createUrlTree(['/auth/login']);
};

