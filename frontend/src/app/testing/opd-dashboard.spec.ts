import { CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { of } from 'rxjs';

import { DoctorDirectoryService } from '../core/services/doctor-directory.service';
import { FloatingAssistantComponent } from '../shared/components/floating-assistant/floating-assistant.component';
import { OPDSummary } from '../features/opd/models/opd.models';
import { OPDOverviewComponent } from '../features/opd/pages/opd-overview/opd-overview.component';
import { OPDService } from '../features/opd/services/opd.service';

const day = '2026-11-01';
const base: OPDSummary = {
  total_visits: 3, waiting_visits: 1, in_consultation_visits: 0, completed_visits: 0, summary_date: day, as_of: '2026-11-01T10:00:00+06:00',
  prescribed_visits: 2, cancelled_visits: 0, not_billed_visits: 1, paid_visits: 1, visits_with_balance: 1,
  gross_amount: '1000.00', discount_amount: '0.00', billed_amount: '1000.00', collected_amount: '700.00', outstanding_amount: '300.00',
  doctor_load: [{ doctor_user_id: 'd1', doctor_name: 'Dr. Rahman', visits: 2 }], unassigned_visits: 1,
  daily_visits: Array.from({ length: 7 }, (_, index) => ({ day: `2026-10-${String(26 + index).padStart(2, '0')}`, visits: index === 6 ? 3 : 0 })),
  live_queue: [],
};

describe('OPD dashboard', () => {
  let opd: jasmine.SpyObj<OPDService>;
  const create = (summary: OPDSummary) => {
    opd = jasmine.createSpyObj('OPDService', ['getSummary']);
    opd.getSummary.and.returnValue(of(summary));
    TestBed.configureTestingModule({ providers: [
      { provide: OPDService, useValue: opd },
      { provide: DoctorDirectoryService, useValue: { listDoctors: () => of([]) } },
      { provide: Router, useValue: jasmine.createSpyObj('Router', ['navigate']) },
    ] });
    // The chat assistant has its own tests and needs the whole app context.
    TestBed.overrideComponent(OPDOverviewComponent, { remove: { imports: [FloatingAssistantComponent] }, add: { schemas: [CUSTOM_ELEMENTS_SCHEMA] } });
    return TestBed.createComponent(OPDOverviewComponent).componentInstance;
  };
  const kpi = (component: OPDOverviewComponent, label: RegExp) => component.dashboardKpis.find((item) => label.test(item.label))!;

  it('reads every figure from the one summary, so cards cannot disagree', () => {
    const component = create(base);
    expect(opd.getSummary).toHaveBeenCalledTimes(1);
    expect(kpi(component, /Registered/).value).toBe('3');
    expect(kpi(component, /Registered/).detail).toBe('1 paid · 1 with a balance · 1 not billed yet');
    expect(kpi(component, /Collected/).value).toContain('700.00');
    expect(kpi(component, /Outstanding/).value).toContain('300.00');
  });

  it('keeps post-consultation patients out of the queue count but shows them', () => {
    const component = create(base);
    expect(kpi(component, /In queue/).value).toBe('1');
    expect(kpi(component, /In queue/).detail).toContain('2 post-consultation');
    expect(component.statusChartItems.find((item) => item.label === 'Post-consultation')?.value).toBe(2);
  });

  it('explains a zero outstanding instead of implying unpaid visits', () => {
    const component = create({ ...base, outstanding_amount: '0.00', visits_with_balance: 0, not_billed_visits: 2 });
    expect(kpi(component, /Outstanding/).detail).toBe('Nothing owed yet · 2 visits not billed');
  });

  it('shows an empty-day message with no invented numbers', () => {
    const component = create({ ...base, total_visits: 0, waiting_visits: 0, prescribed_visits: 0, paid_visits: 0, visits_with_balance: 0, not_billed_visits: 0, billed_amount: '0.00', collected_amount: '0.00', outstanding_amount: '0.00', doctor_load: [], unassigned_visits: 0 });
    expect(component.hasNoVisits).toBeTrue();
    expect(kpi(component, /Registered/).detail).toBe('No registrations yet');
    expect(component.doctorLoadItems).toEqual([]);
  });

  it('names billing-desk visits apart from the doctors', () => {
    const component = create(base);
    expect(component.unassignedNote).toContain('without a doctor');
    expect(component.doctorLoadItems.map((item) => item.label)).toEqual(['Dr. Rahman']);
  });

  it('labels the last trend bar Today only for the current day and opens the matching list from a card', () => {
    const component = create({ ...base, summary_date: new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Dhaka' }) });
    expect(component.weeklyTrendItems[6].label).toBe('Today');
    component.navigateToVisitList(kpi(component, /Outstanding/).query);
    expect(TestBed.inject(Router).navigate).toHaveBeenCalledWith(['/opd/visits'], { queryParams: jasmine.objectContaining({ payment: 'due' }) });
  });
});
