import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';

import { environment } from '../../../environments/environment';

@Injectable({ providedIn: 'root' })
export class ApiBaseService {
  protected readonly http = inject(HttpClient);
  protected readonly apiBaseUrl = environment.apiBaseUrl;

  protected url(path: string): string {
    return `${this.apiBaseUrl}${path}`;
  }
}

