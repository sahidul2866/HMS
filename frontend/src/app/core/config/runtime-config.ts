export const runtimeConfig = {
  apiBaseUrl: 'http://localhost:8000/api/v1',
};

export async function loadRuntimeConfig(): Promise<void> {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), 3000);
  try {
    const response = await fetch('assets/app-config.json', { cache: 'no-store', signal: controller.signal });
    if (!response.ok) {
      return;
    }

    const payload = (await response.json()) as { apiBaseUrl?: string };
    if (payload.apiBaseUrl?.trim()) {
      runtimeConfig.apiBaseUrl = payload.apiBaseUrl.trim();
    }
  } catch {
    // Fall back to the default local API base URL.
  } finally {
    window.clearTimeout(timeoutId);
  }
}
