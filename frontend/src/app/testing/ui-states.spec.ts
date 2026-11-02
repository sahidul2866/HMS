import { TestBed } from '@angular/core/testing';
import { provideHttpClient, withInterceptors, HttpClient, HttpErrorResponse, HttpRequest, HttpResponse } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { of, throwError } from 'rxjs';
import { offlineInterceptor } from '../core/interceptors/offline.interceptor';
import { ConnectionStateService } from '../core/services/connection-state.service';
import { SessionService } from '../core/services/session.service';
import { AuthService } from '../core/services/auth.service';
import { TabRouteReuseStrategy } from '../core/services/tab-route-reuse.strategy';
import { User } from '../core/models/auth.models';
import { runtimeConfig } from '../core/config/runtime-config';
import { AppStateComponent } from '../shared/components/app-state/app-state.component';
import { GlobalFormValidationService } from '../core/services/global-form-validation.service';

const user = { id: 'one', username: 'test', principal_type: 'user', effective_permissions: [] } as unknown as User;

describe('offline records', () => {
  let http: HttpClient;
  let backend: HttpTestingController;
  let state: ConnectionStateService;
  let session: SessionService;
  const url = `${runtimeConfig.apiBaseUrl}/patients`;
  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(withInterceptors([offlineInterceptor])), provideHttpClientTesting()] });
    http = TestBed.inject(HttpClient);
    backend = TestBed.inject(HttpTestingController);
    state = TestBed.inject(ConnectionStateService);
    session = TestBed.inject(SessionService);
    session.setUser(user);
    state.offline.set(false);
  });
  afterEach(() => backend.verify());
  it('keeps a labelled cached copy available offline without another request', () => {
    http.get(url).subscribe();
    backend.expectOne(url).flush([{ id: 'record' }]);
    state.offline.set(true);
    let result: unknown;
    http.get(url).subscribe(value => result = value);
    expect(result).toEqual([{ id: 'record' }]);
    expect(state.cachedAt()).not.toBeNull();
    backend.expectNone(url);
  });
  it('uses loaded records in lighter view and clears the stale label after a live refresh', () => {
    http.get(url).subscribe();
    backend.expectOne(url).flush([{ id: 'record' }]);
    state.lightMode.set(true);
    http.get(url).subscribe();
    backend.expectNone(url);
    expect(state.cachedAt()).not.toBeNull();
    state.lightMode.set(false);
    http.get(url).subscribe();
    backend.expectOne(url).flush([{ id: 'updated' }]);
    expect(state.cachedAt()).toBeNull();
  });
  it('does not cache an old account’s in-flight response after switching accounts', () => {
    http.get(url).subscribe();
    const pending = backend.expectOne(url);
    session.setUser({ ...user, id: 'two' });
    pending.flush([{ id: 'private' }]);
    state.offline.set(true);
    let failed = false;
    http.get(url).subscribe({ error: () => failed = true });
    expect(failed).toBeTrue();
  });
  it('never queues or sends writes offline', () => {
    state.offline.set(true);
    let status: number | undefined;
    http.post(url, {}).subscribe({ error: error => status = error.status });
    expect(status).toBe(0);
    backend.expectNone(url);
  });
  it('clears previous user records when the account changes', () => {
    http.get(url).subscribe();
    backend.expectOne(url).flush([{ id: 'private' }]);
    session.setUser({ ...user, id: 'two' });
    state.offline.set(true);
    let failed = false;
    http.get(url).subscribe({ error: () => failed = true });
    expect(failed).toBeTrue();
  });
  it('invalidates old copies after a successful mutation', () => {
    http.get(url).subscribe();
    backend.expectOne(url).flush([]);
    http.post(url, {}).subscribe();
    backend.expectOne(url).flush({});
    state.offline.set(true);
    let failed = false;
    http.get(url).subscribe({ error: () => failed = true });
    expect(failed).toBeTrue();
  });
});

describe('session recovery', () => {
  beforeEach(() => TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting(), TabRouteReuseStrategy] }));
  it('keeps the authenticated view and its work when refresh is rejected', () => {
    const auth = TestBed.inject(AuthService);
    const session = TestBed.inject(SessionService);
    session.setUser(user);
    spyOn(auth, 'refreshAccessToken').and.returnValue(throwError(() => ({ status: 401 })));
    const clear = spyOn(auth, 'clearSession');
    auth.handleUnauthorized(new HttpRequest('GET', '/patients'), () => of(new HttpResponse())).subscribe({ error: () => {} });
    expect(clear).not.toHaveBeenCalled();
    expect(session.snapshot.user).toBe(user);
    expect(TestBed.inject(ConnectionStateService).sessionExpired()).toBeTrue();
  });
  it('does not expire the session for a network failure during refresh', () => {
    const auth = TestBed.inject(AuthService);
    TestBed.inject(SessionService).setUser(user);
    spyOn(auth, 'refreshAccessToken').and.returnValue(throwError(() => new HttpErrorResponse({ status: 0 })));
    auth.handleUnauthorized(new HttpRequest('GET', '/patients'), () => of(new HttpResponse())).subscribe({ error: () => {} });
    expect(TestBed.inject(ConnectionStateService).sessionExpired()).toBeFalse();
  });
  it('rejects a different account before replacing the session or saving tokens', () => {
    const auth = TestBed.inject(AuthService);
    TestBed.inject(SessionService).setUser(user);
    let failed = false;
    auth.login('test', 'password', user.id).subscribe({ error: () => failed = true });
    TestBed.inject(HttpTestingController).expectOne(`${runtimeConfig.apiBaseUrl}/auth/login`).flush({ user: { ...user, id: 'two' }, tokens: {} });
    expect(failed).toBeTrue();
    expect(TestBed.inject(SessionService).snapshot.user?.id).toBe('one');
  });
  it('opens a modal and keeps it open after an incorrect password', async () => {
    TestBed.inject(SessionService).setUser(user);
    const fixture = TestBed.createComponent(AppStateComponent);
    fixture.detectChanges();
    TestBed.inject(ConnectionStateService).sessionExpired.set(true);
    fixture.detectChanges();
    await fixture.whenStable();
    expect(fixture.nativeElement.querySelector('dialog').open).toBeTrue();
    spyOn(TestBed.inject(AuthService), 'login').and.returnValue(throwError(() => ({ status: 401 })));
    fixture.componentInstance.password = 'incorrect';
    fixture.componentInstance.resume();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('dialog').open).toBeTrue();
    expect(fixture.nativeElement.textContent).toContain('password was not accepted');
    fixture.destroy();
  });
});

describe('field validation', () => {
  it('opens collapsed sections before focusing the field that needs correction', () => {
    const service = TestBed.inject(GlobalFormValidationService);
    const form = document.createElement('form');
    form.innerHTML = '<details><summary>Optional settings</summary><details><summary>Reference</summary><label>Reason<input required></label></details></details>';
    document.body.append(form);
    try {
      service.start();
      form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
      expect(Array.from(form.querySelectorAll('details')).every(details => details.open)).toBeTrue();
      expect(document.activeElement).toBe(form.querySelector('input'));
    } finally {
      form.remove();
    }
  });

  it('keeps small selects compact and adds search when an async catalog grows', async () => {
    const service = TestBed.inject(GlobalFormValidationService);
    const wrapper = document.createElement('label');
    wrapper.innerHTML = 'Service<select><option value="">Select a service</option><option value="chosen" selected>Consultation</option></select>';
    document.body.append(wrapper);
    try {
      service.start();
      expect(wrapper.querySelector('input')).toBeNull();
      const select = wrapper.querySelector('select')!;
      for (let index = 0; index < 20; index++) select.add(new Option(`Laboratory ${index}`, `lab-${index}`));
      await new Promise(resolve => setTimeout(resolve, 0));
      const search = wrapper.querySelector<HTMLInputElement>('input[type="search"]')!;
      expect(search).not.toBeNull();
      search.value = 'Laboratory 12';
      search.dispatchEvent(new Event('input', { bubbles: true }));
      expect(select.value).toBe('chosen');
      expect(select.options[0].hidden).toBeFalse();
      expect(Array.from(select.options).filter(option => !option.hidden).map(option => option.value)).toEqual(['', 'lab-12']);
      expect(wrapper.querySelectorAll('input').length).toBe(1);
    } finally {
      wrapper.remove();
    }
  });

  it('blocks invalid submissions and links a field to its correction message', async () => {
    const service = TestBed.inject(GlobalFormValidationService);
    service.start();
    const form = document.createElement('form');
    form.innerHTML = '<label for="state-email">Email</label><input id="state-email" type="email" value="invalid" required aria-describedby="help"><span id="help">Work email</span>';
    document.body.append(form);
    const event = new Event('submit', { bubbles: true, cancelable: true });
    form.dispatchEvent(event);
    const input = form.querySelector('input')!;
    expect(event.defaultPrevented).toBeTrue();
    expect(input.getAttribute('aria-invalid')).toBe('true');
    expect(form.querySelector('.app-field-error')?.textContent).toContain('valid email address');
    input.value = 'test@example.com';
    input.dispatchEvent(new Event('input', { bubbles: true }));
    await Promise.resolve();
    expect(form.querySelector('.app-field-error')).toBeNull();
    expect(input.getAttribute('aria-describedby')).toBe('help');
    form.remove();
  });
});
