const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  body?: unknown;
  headers?: Record<string, string>;
}

function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  const accessToken = localStorage.getItem('access_token');
  const apiKey = localStorage.getItem('api_key');
  
  if (accessToken) {
    headers['Authorization'] = `Bearer ${accessToken}`;
  } else if (apiKey) {
    headers['X-Api-Key'] = apiKey;
  }
  
  return headers;
}

export async function api<T = unknown>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const { method = 'GET', body, headers = {} } = options;

  const response = await fetch(`${API_BASE}${endpoint}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
      ...headers,
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });

  if (response.status === 204) {
    return undefined as T;
  }

  const data = await response.json().catch(() => ({} as T));

  if (!response.ok) {
    const error = (data as { detail?: string }).detail || `HTTP ${response.status}`;
    throw new Error(error);
  }

  return data;
}

// Helper for GET requests with search params
export async function apiGet<T = unknown>(
  endpoint: string,
  params?: Record<string, string | number | boolean | undefined>
): Promise<T> {
  const searchParams = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        searchParams.append(key, String(value));
      }
    });
  }
  const query = searchParams.toString();
  return api<T>(query ? `${endpoint}?${query}` : endpoint);
}

// Auth helpers
export async function login(username: string, password: string) {
  return api<{ access_token: string; refresh_token: string; token_type: string }>(
    '/auth/login',
    {
      method: 'POST',
      body: { username, password },
    }
  );
}

export async function refreshToken(refreshToken: string) {
  return api<{ access_token: string; refresh_token: string; token_type: string }>(
    '/auth/refresh',
    {
      method: 'POST',
      body: { refresh_token: refreshToken },
    }
  );
}

export async function logout() {
  return api('/auth/logout', { method: 'POST' });
}