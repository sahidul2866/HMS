import { fakeAsync, flushMicrotasks, tick } from '@angular/core/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { runtimeConfig } from '../core/config/runtime-config';
import { TestBed } from '@angular/core/testing';
import { convertToParamMap, ActivatedRoute, Router } from '@angular/router';
import { of, throwError } from 'rxjs';
import { QueueAnnouncementService } from '../core/services/queue-announcement.service';
import { QueueToken } from '../features/queue/models/queue.models';
import { OPDVisitListComponent } from '../features/opd/pages/opd-visit-list/opd-visit-list.component';
import { OPDService } from '../features/opd/services/opd.service';
import { PharmacyService } from '../features/pharmacy/services/pharmacy.service';
import { ConfigurationService } from '../features/configuration/services/configuration.service';
import { DoctorDirectoryService } from '../core/services/doctor-directory.service';
import { SessionService } from '../core/services/session.service';
import { OPDVisit } from '../features/opd/models/opd.models';
import { buildOPDPrescriptionHtml } from '../shared/utils/opd-prescription-printer';
import { User } from '../core/models/auth.models';

const testVisit = { id: 'visit', status: 'waiting', visit_number: 'OPD-TEST', patient: { id: 'patient', first_name: 'Test', last_name: 'Patient', patient_number: 'P1' }, orders: [], consulting_doctor_name: 'Dr Test', department_name: 'Medicine', visit_date: '2026-10-31' } as unknown as OPDVisit;

describe('OPD consultation controls', () => {
  let opd: jasmine.SpyObj<OPDService>;
  let component: OPDVisitListComponent;
  beforeEach(() => {
    opd = jasmine.createSpyObj('OPDService', ['listVisits', 'getVisit', 'getPatientVisits', 'updateStatus', 'updateConsultation', 'finalizePrescription']);
    opd.listVisits.and.returnValue(of([testVisit]));
    opd.getPatientVisits.and.returnValue(of([]));
    opd.updateStatus.and.returnValue(of({ ...testVisit, status: 'in_consultation' }));
    TestBed.configureTestingModule({ providers: [
      { provide: OPDService, useValue: opd },
      { provide: PharmacyService, useValue: { prescribingMedicines: () => of({ items: [] }), listInvestigationSettings: () => of({ items: [] }) } },
      { provide: ConfigurationService, useValue: { workspace: () => of({ profiles: [] }) } },
      { provide: DoctorDirectoryService, useValue: { listDoctors: () => of([]) } },
      { provide: ActivatedRoute, useValue: { queryParamMap: of(convertToParamMap({})) } },
      { provide: Router, useValue: jasmine.createSpyObj('Router', ['navigate']) },
    ] });
    TestBed.inject(SessionService).setUser({ id: 'doctor', roles: [{ is_doctor_role: true }], effective_permissions: ['opd.visit.manage', 'opd.prescribe'] } as unknown as User);
    component = TestBed.createComponent(OPDVisitListComponent).componentInstance;
  });
  it('starts the consultation and opens its prescription editor', () => {
    component.startVisit(testVisit);
    expect(opd.updateStatus).toHaveBeenCalledWith('visit', 'in_consultation');
    expect(component.selectedVisit?.status).toBe('in_consultation');
    expect(TestBed.inject(Router).navigate).not.toHaveBeenCalled();
  });
  it('keeps the existing editor intact when starting is rejected', () => {
    opd.updateStatus.and.returnValue(throwError(() => ({ message: 'Doctor already has an active patient' })));
    component.selectedVisit = testVisit;
    component.startVisit(testVisit);
    expect(component.selectedVisit).toBe(testVisit);
    expect(component.savingConsultation).toBeFalse();
  });
  it('keeps unsaved clinical edits when closing is cancelled', () => {
    component.startVisit(testVisit);
    component.prescriptionDraft.final_diagnosis = 'Unsaved diagnosis';
    spyOn(window, 'confirm').and.returnValue(false);
    component.closeVisit();
    expect(component.hasUnsavedChanges()).toBeTrue();
    expect(component.selectedVisit).not.toBeNull();
  });
  it('finalizes the saved consultation once and resets its busy state', () => {
    spyOn(window, 'confirm').and.returnValue(true);
    component.selectedVisit = { ...testVisit, status: 'in_consultation' };
    opd.updateConsultation.and.returnValue(of(component.selectedVisit));
    opd.finalizePrescription.and.returnValue(of({ ...testVisit, status: 'prescribed', queue_status: 'completed' }));
    component.finalizePrescription();
    expect(opd.finalizePrescription).toHaveBeenCalled();
    expect(component.selectedVisit?.queue_status).toBe('completed');
    expect(component.savingConsultation).toBeFalse();
  });
});

describe('PA queue announcements', () => {
  let pa: QueueAnnouncementService;
  let backend: HttpTestingController;
  let speak: jasmine.Spy;
  const token = (called_at: string): QueueToken => ({ id: 'serial', token_number: 'DR-A-001', token_sequence: 1, status: 'called', called_at } as QueueToken);
  const enable = (neural = false, tokens: QueueToken[] = []) => {
    pa.enable(tokens);
    backend.expectOne(`${runtimeConfig.apiBaseUrl}/queue/speech/config`).flush({ available: neural });
    flushMicrotasks();
  };
  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    pa = TestBed.inject(QueueAnnouncementService);
    backend = TestBed.inject(HttpTestingController);
    speak = spyOn(window.speechSynthesis, 'speak').and.callFake(utterance => {
      queueMicrotask(() => utterance.onend?.(new Event('end') as SpeechSynthesisEvent));
    });
    spyOn(window.speechSynthesis, 'cancel');
  });
  afterEach(() => { pa.disable(); backend.verify(); });
  it('announces new calls once and supports intentional repeats using the labelled fallback', fakeAsync(() => {
    enable();
    speak.calls.reset();
    const first = token(new Date().toISOString());
    pa.consume([first], () => 'Doctor Test, room 12');
    pa.consume([first], () => 'Doctor Test, room 12');
    flushMicrotasks();
    expect(speak).toHaveBeenCalledTimes(1);
    expect((speak.calls.mostRecent().args[0] as SpeechSynthesisUtterance).text).toBe('Serial 1. Please proceed to Doctor Test, room 12.');
    expect(pa.engine()).toContain('not configured');
    pa.consume([token(new Date(Date.now() + 1000).toISOString())], () => 'Doctor Test, room 12');
    flushMicrotasks();
    expect(speak).toHaveBeenCalledTimes(2);
  }));
  it('does not replay existing or historical calls when enabled', fakeAsync(() => {
    const existing = token(new Date().toISOString());
    enable(false, [existing]);
    speak.calls.reset();
    pa.consume([existing, { ...token(new Date(Date.now() - 180000).toISOString()), id: 'old' }], () => 'Doctor Test');
    flushMicrotasks();
    expect(speak).not.toHaveBeenCalled();
  }));
  it('stops announcements when audio is disabled', fakeAsync(() => {
    enable();
    pa.disable();
    speak.calls.reset();
    pa.consume([token(new Date().toISOString())], () => 'Doctor Test');
    flushMicrotasks();
    expect(speak).not.toHaveBeenCalled();
    expect(window.speechSynthesis.cancel).toHaveBeenCalled();
  }));
  it('requests neural MP3 audio and releases its object URL after playback', fakeAsync(() => {
    let element: HTMLAudioElement;
    spyOn(window, 'Audio').and.callFake(function() {
      element = document.createElement('audio');
      spyOn(element, 'play').and.returnValue(Promise.resolve());
      spyOn(element, 'pause');
      return element;
    });
    const createUrl = spyOn(URL, 'createObjectURL').and.returnValue('blob:neural-test');
    const revoke = spyOn(URL, 'revokeObjectURL');
    enable(true);
    const request = backend.expectOne(`${runtimeConfig.apiBaseUrl}/queue/speech`);
    expect(request.request.body.language).toBe('en-US');
    request.flush(new Blob(['mp3'], { type: 'audio/mpeg' }));
    flushMicrotasks();
    expect(createUrl).toHaveBeenCalled();
    expect(speak).not.toHaveBeenCalled();
    element!.dispatchEvent(new Event('ended'));
    flushMicrotasks();
    expect(revoke).toHaveBeenCalledWith('blob:neural-test');
    expect(pa.message()).toContain('Neural announcement played');
  }));
  it('falls back once when the neural provider fails', fakeAsync(() => {
    enable(true);
    backend.expectOne(`${runtimeConfig.apiBaseUrl}/queue/speech`).flush(new Blob(['unavailable'], { type: 'application/json' }), { status: 502, statusText: 'Bad Gateway' });
    flushMicrotasks();
    expect(speak).toHaveBeenCalledTimes(1);
    expect(pa.engine()).toContain('neural request failed');
  }));
  it('cancels pending synthesis without playing late audio after disable', fakeAsync(() => {
    enable(true);
    const request = backend.expectOne(`${runtimeConfig.apiBaseUrl}/queue/speech`);
    pa.disable();
    flushMicrotasks();
    expect(request.cancelled).toBeTrue();
    expect(speak).not.toHaveBeenCalled();
  }));
  it('uses device speech when the neural config request times out', fakeAsync(() => {
    pa.enable([]);
    const config = backend.expectOne(`${runtimeConfig.apiBaseUrl}/queue/speech/config`);
    tick(3001);
    flushMicrotasks();
    expect(config.cancelled).toBeTrue();
    expect(speak).toHaveBeenCalledTimes(1);
    expect(pa.engine()).toContain('unavailable');
  }));
});

describe('prescription printing', () => {
  it('keeps long medicine lists and escapes entered text without clipping the sheet', () => {
    const orders = Array.from({ length: 35 }, (_, index) => ({ id: String(index), order_type: 'prescription', item_name: `Medicine ${index}`, instructions: '<script>unsafe</script>', quantity: 1, status: 'pending', created_at: '2026-10-31T10:00:00Z' }));
    const html = buildOPDPrescriptionHtml({ visit: { ...testVisit, orders } as unknown as OPDVisit });
    expect(html).toContain('Medicine 34');
    expect(html).not.toContain('<script>unsafe</script>');
    expect(html).toContain('&lt;script&gt;unsafe&lt;/script&gt;');
    expect(html).not.toContain('max-height: 100vh');
    expect(html).toContain('height: auto; overflow: visible');
  });
});
