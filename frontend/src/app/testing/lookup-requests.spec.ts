import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { DoctorDirectoryService } from '../core/services/doctor-directory.service';
import { SessionService } from '../core/services/session.service';

describe('lookup requests', () => {
  const setup = (permissions: string[]) => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), { provide: SessionService, useValue: { hasAnyPermission: (codes: string[]) => codes.some((code) => permissions.includes(code)) } }],
    });
    return { directory: TestBed.inject(DoctorDirectoryService), backend: TestBed.inject(HttpTestingController) };
  };

  it('does not ask for the doctor list a role may not read', () => {
    const { directory, backend } = setup(['queue.view']);
    let doctors: unknown[] | undefined;
    directory.listDoctors().subscribe((list) => (doctors = list));
    backend.expectNone((request) => request.url.includes('/users/doctors'));
    expect(doctors).toEqual([]);
  });

  it('asks for the doctor list when any of the gating rights is held', () => {
    const { directory, backend } = setup(['opd.view']);
    directory.listDoctors().subscribe();
    backend.expectOne((request) => request.url.includes('/users/doctors')).flush([]);
  });
});
