import '../app/core/models/runtime-config';

const runtimeApiBaseUrl = window.__HMS_CONFIG__?.apiBaseUrl?.trim();

export const environment = {
  production: false,
  apiBaseUrl: runtimeApiBaseUrl || 'http://localhost:8000/api/v1',
};
