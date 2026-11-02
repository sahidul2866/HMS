import { TestBed, fakeAsync, flushMicrotasks, tick } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { GlobalScannerComponent } from '../shared/components/global-scanner/global-scanner.component';
import { ScannerService } from '../features/scanner/services/scanner.service';
import { NotificationService } from '../core/services/notification.service';

describe('scanner camera lifecycle', () => {
  let detectorDescriptor: PropertyDescriptor | undefined;
  beforeEach(() => {
    detectorDescriptor = Object.getOwnPropertyDescriptor(window, 'BarcodeDetector');
    Object.defineProperty(window, 'BarcodeDetector', { configurable: true, value: class { detect() { return Promise.resolve([]); } } });
    TestBed.configureTestingModule({ imports: [GlobalScannerComponent], providers: [provideRouter([]),
      { provide: ScannerService, useValue: {} },
      { provide: NotificationService, useValue: { error: jasmine.createSpy(), success: jasmine.createSpy() } },
    ] });
  });
  afterEach(() => {
    if (detectorDescriptor) Object.defineProperty(window, 'BarcodeDetector', detectorDescriptor);
    else delete (window as any).BarcodeDetector;
  });

  it('stops a late camera stream when the user closes the scanner during permission approval', fakeAsync(() => {
    let approve!: (stream: MediaStream) => void;
    spyOn(navigator.mediaDevices, 'getUserMedia').and.returnValue(new Promise(resolve => approve = resolve));
    const fixture = TestBed.createComponent(GlobalScannerComponent);
    const component = fixture.componentInstance;
    component.show();component.startCamera();component.close();
    const stop = jasmine.createSpy('stop');
    approve({ getTracks: () => [{ stop }] } as unknown as MediaStream);
    flushMicrotasks();
    expect(stop).toHaveBeenCalled();
    expect(component.cameraActive).toBeFalse();
    expect(component.cameraStarting).toBeFalse();
  }));

  it('attaches the stream after the video element is rendered and releases it on close', fakeAsync(() => {
    const stream = new MediaStream();
    const stop = jasmine.createSpy('stop');
    spyOn(stream, 'getTracks').and.returnValue([{ stop }] as unknown as MediaStreamTrack[]);
    spyOn(navigator.mediaDevices, 'getUserMedia').and.returnValue(Promise.resolve(stream));
    spyOn(HTMLMediaElement.prototype, 'play').and.returnValue(Promise.resolve());
    const fixture = TestBed.createComponent(GlobalScannerComponent);
    const component = fixture.componentInstance;
    component.show();component.startCamera();flushMicrotasks();fixture.detectChanges();tick(0);
    const video = fixture.nativeElement.querySelector('video') as HTMLVideoElement;
    expect(video.srcObject).toBe(stream);
    component.close();
    expect(stop).toHaveBeenCalled();
    tick(300);
  }));

  it('offers USB and manual entry after permission denial', fakeAsync(() => {
    spyOn(navigator.mediaDevices, 'getUserMedia').and.returnValue(Promise.reject({ name: 'NotAllowedError' }));
    const fixture = TestBed.createComponent(GlobalScannerComponent);
    fixture.componentInstance.show();fixture.componentInstance.startCamera();flushMicrotasks();
    expect(fixture.componentInstance.message).toContain('permission was denied');
    expect(fixture.componentInstance.message).toContain('USB scanner');
    expect(fixture.componentInstance.cameraStarting).toBeFalse();
  }));
});
