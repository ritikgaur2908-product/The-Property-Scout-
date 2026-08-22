const rawBase = import.meta.env.VITE_API_URL || 'https://web-production-4b14e.up.railway.app';
let sanitized = (rawBase || '').trim();
if (sanitized.startsWith('ttps://')) sanitized = 'https://' + sanitized.slice(7);
else if (sanitized.startsWith('ttp://')) sanitized = 'http://' + sanitized.slice(6);
else if (!sanitized.startsWith('http://') && !sanitized.startsWith('https://')) sanitized = 'https://' + sanitized;
const BASE_URL = sanitized.replace(/\/$/, '');

export async function fetchApi<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.detail || `API Error: ${response.status}`);
  }

  return response.json();
}
