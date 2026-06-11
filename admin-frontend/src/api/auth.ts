import { login as apiLogin, logout as apiLogout, refreshToken } from './client';

// Re-export for convenience
export { apiLogin as login, apiLogout as logout };

// Auth state management
export function setTokens(accessToken: string, refreshToken: string) {
  localStorage.setItem('access_token', accessToken);
  localStorage.setItem('refresh_token', refreshToken);
}

export function clearTokens() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('api_key');
}

export function getAccessToken(): string | null {
  return localStorage.getItem('access_token');
}

export function getRefreshToken(): string | null {
  return localStorage.getItem('refresh_token');
}

export function getApiKey(): string | null {
  return localStorage.getItem('api_key');
}

export function setApiKey(apiKey: string) {
  localStorage.setItem('api_key', apiKey);
}

export async function handleLogout() {
  try {
    await apiLogout();
  } catch {
    // Ignore errors during logout
  } finally {
    clearTokens();
  }
}

export async function handleRefresh() {
  const refresh = getRefreshToken();
  if (!refresh) {
    throw new Error('No refresh token');
  }
  
  const tokens = await refreshToken(refresh);
  setTokens(tokens.access_token, tokens.refresh_token);
  return tokens.access_token;
}