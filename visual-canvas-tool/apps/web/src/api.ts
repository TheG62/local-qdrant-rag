import type { Board, Share, User } from './types';

const API_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:4000';
export const WS_URL = (import.meta.env.VITE_WS_URL as string) || 'ws://localhost:4000';

let token: string | null = localStorage.getItem('vct_token');

export function setToken(t: string | null) {
  token = t;
  if (t) localStorage.setItem('vct_token', t);
  else localStorage.removeItem('vct_token');
}
export function getToken() {
  return token;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_URL}/api${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error || `Fehler ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  register: (name: string, email: string, password: string) =>
    request<{ token: string; user: User }>('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ name, email, password }),
    }),
  login: (email: string, password: string) =>
    request<{ token: string; user: User }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  me: () => request<{ user: User }>('/me'),
  deleteAccount: () => request<{ ok: boolean }>('/me', { method: 'DELETE' }),

  listBoards: () => request<{ boards: Board[] }>('/boards'),
  trash: () => request<{ boards: Board[] }>('/boards/trash'),
  createBoard: (title: string, parentId?: string | null) =>
    request<{ board: Board }>('/boards', {
      method: 'POST',
      body: JSON.stringify({ title, parentId }),
    }),
  getBoard: (id: string) =>
    request<{ board: Board; children: Board[] }>(`/boards/${id}`),
  updateBoard: (id: string, patch: { title?: string; parentId?: string | null }) =>
    request<{ board: Board }>(`/boards/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(patch),
    }),
  duplicateBoard: (id: string) =>
    request<{ board: Board }>(`/boards/${id}/duplicate`, { method: 'POST' }),
  deleteBoard: (id: string) =>
    request<{ ok: boolean }>(`/boards/${id}`, { method: 'DELETE' }),
  restoreBoard: (id: string) =>
    request<{ board: Board }>(`/boards/${id}/restore`, { method: 'POST' }),

  listShares: (id: string) => request<{ shares: Share[] }>(`/boards/${id}/shares`),
  share: (id: string, body: { email?: string; role?: string; publicLink?: boolean }) =>
    request<{ share: Share }>(`/boards/${id}/shares`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  removeShare: (shareId: string) =>
    request<{ ok: boolean }>(`/shares/${shareId}`, { method: 'DELETE' }),
  publicBoard: (tokenStr: string) =>
    request<{ board: { id: string; title: string }; token: string }>(`/public/${tokenStr}`),

  search: (q: string) =>
    request<{ results: { boardId: string; title: string; snippet: string }[] }>(
      `/search?q=${encodeURIComponent(q)}`,
    ),
  activity: (id: string) =>
    request<{ activities: { id: string; actor: string; action: string; timestamp: string }[] }>(
      `/boards/${id}/activity`,
    ),
  exportBoard: (id: string) => request<unknown>(`/boards/${id}/export`),
  linkPreview: (url: string) =>
    request<{ title: string; description: string; image: string; siteName: string }>(
      `/link-preview?url=${encodeURIComponent(url)}`,
    ),
};
