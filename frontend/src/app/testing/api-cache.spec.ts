import { of } from 'rxjs';
import { ApiCacheService } from '../core/services/api-cache.service';

describe('persistent lookup cache', () => {
  let cache: ApiCacheService;
  beforeEach(() => {
    sessionStorage.clear();
    cache = new ApiCacheService();
  });
  afterEach(() => jasmine.clock().uninstall());

  const read = (service: ApiCacheService, rows: string[], calls: { n: number }) => {
    let result: string[] = [];
    service.getPersistent('lookup', () => { calls.n++; return of(rows); }).subscribe((value) => (result = value));
    return result;
  };

  it('does not remember an empty list, so rows added by others appear on the next read', () => {
    const calls = { n: 0 };
    expect(read(cache, [], calls)).toEqual([]);
    expect(read(new ApiCacheService(), ['Morning'], calls)).toEqual(['Morning']);
    expect(calls.n).toBe(2);
  });

  it('reuses a filled list inside the window and asks again after it', () => {
    jasmine.clock().install();
    jasmine.clock().mockDate(new Date(2026, 10, 1, 9, 0, 0));
    const calls = { n: 0 };
    read(cache, ['Morning'], calls);
    read(new ApiCacheService(), ['Morning'], calls);
    expect(calls.n).toBe(1);
    jasmine.clock().mockDate(new Date(2026, 10, 1, 9, 3, 0));
    read(new ApiCacheService(), ['Morning', 'Night'], calls);
    expect(calls.n).toBe(2);
  });

  it('drops an old-format stored entry instead of trusting it', () => {
    sessionStorage.setItem('hms-api-cache:lookup', JSON.stringify(['stale']));
    expect(read(cache, ['fresh'], { n: 0 })).toEqual(['fresh']);
  });
});
