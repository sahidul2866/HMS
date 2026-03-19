export const runtimeConfig = {
  apiBaseUrl: 'http://localhost:8000/api/v1',
};

export async function loadRuntimeConfig(): Promise<void> {
  try {
    const response = await fetch('assets/app-config.json', { cache: 'no-store' });
    if (!response.ok) {
      return;
    }

    const payload = (await response.json()) as { apiBaseUrl?: string };
    if (payload.apiBaseUrl?.trim()) {
      runtimeConfig.apiBaseUrl = payload.apiBaseUrl.trim();
    }
  } catch {
    // Fall back to the default local API base URL.
  }
}
