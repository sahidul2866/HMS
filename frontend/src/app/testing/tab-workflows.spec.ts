import { TestBed } from '@angular/core/testing';
import { NavigationEnd, Router } from '@angular/router';
import { Subject } from 'rxjs';
import { TabService } from '../core/services/tab.service';
import { TabRouteReuseStrategy } from '../core/services/tab-route-reuse.strategy';

describe('connected module navigation',()=>{
 it('keeps the requested route and earlier work after more than eight pages',()=>{
  sessionStorage.removeItem('hms.tabs');
  const events=new Subject<NavigationEnd>(),navigate=jasmine.createSpy('navigateByUrl');
  const evict=jasmine.createSpy('evict');
  TestBed.configureTestingModule({providers:[TabService,{provide:Router,useValue:{events,routerState:{snapshot:{root:{data:{tabLabel:'Workflow'},firstChild:null}}},navigateByUrl:navigate}},{provide:TabRouteReuseStrategy,useValue:{evict,clear:()=>{}}}]});
  const service=TestBed.inject(TabService);
  const paths=['dashboard','blood-bank/donors','blood-bank/screening','blood-bank/collection','blood-bank/testing','blood-bank/components','blood-bank/requests','blood-bank/crossmatch','blood-bank/issue','blood-bank/transfusion'];
  paths.forEach((path,index)=>events.next(new NavigationEnd(index,'/'+path,'/'+path)));
  expect(service.activePath()).toBe('/blood-bank/transfusion');expect(service.tabs().length).toBe(10);expect(navigate).not.toHaveBeenCalled();expect(evict).not.toHaveBeenCalled();
  service.clear();
 });
});
