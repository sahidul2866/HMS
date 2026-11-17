import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router, RouterOutlet } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';

import { appRoutes } from '../app.routes';
import { permissionGuard } from '../core/guards/permission.guard';
import { User } from '../core/models/auth.models';
import { NotificationService } from '../core/services/notification.service';
import { SessionService } from '../core/services/session.service';
import { BreadcrumbsComponent } from '../shared/components/breadcrumbs/breadcrumbs.component';

@Component({ standalone: true, template: 'Page' })
class PageComponent {}

@Component({
  standalone: true,
  imports: [BreadcrumbsComponent, RouterOutlet],
  template: '<app-breadcrumbs /><router-outlet />',
})
class ShellComponent {}

describe('account-aware Home navigation', () => {
  for (const account of [
    { name: 'patient', permissions: ['patient.portal.view'], patientId: 'patient-1', home: '/portal' },
    { name: 'dashboard staff', permissions: ['dashboard.view'], patientId: null, home: '/dashboard' },
    { name: 'billing staff', permissions: ['billing.view'], patientId: null, home: '/billing' },
  ]) {
    it(`returns ${account.name} to their allowed home without a permission warning`, async () => {
      const rootRedirect = appRoutes.find(route => route.path === '' && route.children)
        ?.children?.find(route => route.path === '');
      expect(rootRedirect).toBeDefined();
      TestBed.configureTestingModule({ providers: [provideRouter([{
        path: '', component: ShellComponent, children: [
          rootRedirect!,
          { path: 'profile', component: PageComponent, data: { tabLabel: 'Profile' } },
          ...[
            { path: 'portal', permission: 'patient.portal.view' },
            { path: 'dashboard', permission: 'dashboard.view' },
            { path: 'billing', permission: 'billing.view' },
          ].map(route => ({
            path: route.path, component: PageComponent, canActivate: [permissionGuard],
            data: { permissions: [route.permission], tabLabel: route.path },
          })),
        ],
      }])] });
      TestBed.inject(SessionService).setUser({
        id: account.name, patient_id: account.patientId,
        effective_permissions: account.permissions,
      } as User);
      const notifications = TestBed.inject(NotificationService);
      const harness = await RouterTestingHarness.create('/profile');
      const home = harness.routeNativeElement!.querySelector<HTMLAnchorElement>('a.crumb')!;
      expect(home.textContent?.trim()).toBe('Home');
      home.click();
      await harness.fixture.whenStable();
      expect(TestBed.inject(Router).url).toBe(account.home);
      expect(notifications.items()).toEqual([]);

      await harness.navigateByUrl('/');
      expect(TestBed.inject(Router).url).toBe(account.home);
      expect(notifications.items()).toEqual([]);
    });
  }
});
