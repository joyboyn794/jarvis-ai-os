const API_BASE = '/api/v1';

interface RequestOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
  token?: string;
}

class ApiClient {
  private getHeaders(tokenOverride?: string): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    // Use explicit token if provided (avoids localStorage race condition)
    if (tokenOverride) {
      headers['Authorization'] = `Bearer ${tokenOverride}`;
      return headers;
    }

    // Fallback: Get token from localStorage (set by zustand persist)
    try {
      const stored = localStorage.getItem('jarvis-auth');
      if (stored) {
        const parsed = JSON.parse(stored);
        const token = parsed.state?.accessToken;
        if (token) {
          headers['Authorization'] = `Bearer ${token}`;
        }
      }
    } catch {
      // ignore parse errors
    }

    return headers;
  }

  async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const { method = 'GET', body, headers: extraHeaders, token } = options;

    const response = await fetch(`${API_BASE}${endpoint}`, {
      method,
      headers: { ...this.getHeaders(token), ...extraHeaders },
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return response.json();
  }

  async get<T>(endpoint: string, token?: string): Promise<T> {
    return this.request<T>(endpoint, { token });
  }

  async post<T>(endpoint: string, body?: unknown): Promise<T> {
    return this.request<T>(endpoint, { method: 'POST', body });
  }

  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' });
  }
}

export const apiClient = new ApiClient();
