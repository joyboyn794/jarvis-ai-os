import { apiClient } from './apiClient';

interface User {
  id: string;
  email: string;
  display_name: string;
  is_active: boolean;
  created_at: string;
}

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

interface Conversation {
  id: string;
  title: string;
  model: string;
  message_count: number;
  last_message: string | null;
  created_at: string;
  updated_at: string;
}

interface Message {
  id: string;
  conversation_id: string;
  role: string;
  content: string;
  token_count: number;
  created_at: string;
}

interface ConversationDetail extends Conversation {
  messages: Message[];
}

// ── Auth ───────────────────────────────────────────────────

export const authApi = {
  register: (email: string, password: string, display_name: string) =>
    apiClient.post<User>('/auth/register', { email, password, display_name }),

  login: (email: string, password: string) =>
    apiClient.post<TokenResponse>('/auth/login', { email, password }),

  refresh: (refresh_token: string) =>
    apiClient.post<TokenResponse>('/auth/refresh', { refresh_token }),

  getMe: (token?: string) => apiClient.get<User>('/auth/me', token),
};

// ── Chat ───────────────────────────────────────────────────

export const chatApi = {
  listConversations: (limit = 50, offset = 0) =>
    apiClient.get<Conversation[]>(`/chat/conversations?limit=${limit}&offset=${offset}`),

  getConversation: (id: string) =>
    apiClient.get<ConversationDetail>(`/chat/conversations/${id}`),

  deleteConversation: (id: string) =>
    apiClient.delete<void>(`/chat/conversations/${id}`),

  sendMessage: (message: string, conversationId?: string, useMemory = true) =>
    apiClient.post<Message>('/chat/send', {
      message,
      conversation_id: conversationId || null,
      use_memory: useMemory,
    }),
};

// ── WebSocket ──────────────────────────────────────────────

export function createChatWebSocket(token: string): WebSocket {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  return new WebSocket(`${protocol}//${host}/api/v1/chat/ws?token=${token}`);
}

// ── Voice ──────────────────────────────────────────────────

export const voiceApi = {
  transcribe: async (audioBlob: Blob, language?: string): Promise<string> => {
    const formData = new FormData();
    formData.append('file', audioBlob, 'recording.wav');
    if (language) {
      formData.append('language', language);
    }

    const headers: Record<string, string> = {};
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
      // ignore
    }

    const response = await fetch('/api/v1/voice/transcribe', {
      method: 'POST',
      headers,
      body: formData,
    });

    if (!response.ok) {
      throw new Error('Transcription failed');
    }

    const data = await response.json();
    return data.text;
  },

  speak: async (text: string, voice = 'alloy', speed = 1.0): Promise<ArrayBuffer> => {
    const headers: Record<string, string> = {};
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
      // ignore
    }

    const params = new URLSearchParams({ text, voice, speed: speed.toString() });
    const response = await fetch(`/api/v1/voice/speak?${params}`, { headers });

    if (!response.ok) {
      throw new Error('TTS failed');
    }

    return response.arrayBuffer();
  },
};

// ── Memory ─────────────────────────────────────────────────

export const memoryApi = {
  search: (query: string, limit = 10, memory_type?: string) =>
    apiClient.post('/memory/search', { query, limit, memory_type }),
};
