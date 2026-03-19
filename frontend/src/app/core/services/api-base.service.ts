import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';

import { runtimeConfig } from '../config/runtime-config';

@Injectable({ providedIn: 'root' })
export class ApiBaseService {
  protected readonly http = inject(HttpClient);

  protected url(path: string): string {
    return `${runtimeConfig.apiBaseUrl}${path}`;
  }
}
