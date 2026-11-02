import { TestBed } from '@angular/core/testing';
import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { authInterceptor } from '../core/interceptors/auth.interceptor';
import { AuthService } from '../core/services/auth.service';
import { TokenStorageService } from '../core/services/token-storage.service';

describe('authenticated session bootstrap',()=>{
 it('attaches the token when refresh is suppressed for the current-user check',()=>{
  TestBed.configureTestingModule({providers:[provideHttpClient(withInterceptors([authInterceptor])),provideHttpClientTesting(),{provide:AuthService,useValue:{}},{provide:TokenStorageService,useValue:{getAccessToken:()=> 'synthetic-token'}}]});
  const http=TestBed.inject(HttpClient);const backend=TestBed.inject(HttpTestingController);
  http.get('/api/v1/auth/me',{headers:{'X-Skip-Auth-Refresh':'1'}}).subscribe();
  const request=backend.expectOne('/api/v1/auth/me');expect(request.request.headers.get('Authorization')).toBe('Bearer synthetic-token');request.flush({id:'synthetic-user'});backend.verify();
 });
});
