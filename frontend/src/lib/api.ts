import type { components } from './api-types';

export type Schemas = components['schemas'];
export type Me = Schemas['MeOut'];
export type TokenOut = Schemas['TokenOut'];

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly details?: unknown,
  ) {
    super(message);
  }
}

const BASE = '/api/v1';
const DEVICE_KEY = 'fp_device_token';

// ---- access token: memory only (DECISIONS.md #3) -------------------------------------------

let accessToken: string | null = null;
type Listener = (token: string | null) => void;
const listeners = new Set<Listener>();

export const tokenStore = {
  get: () => accessToken,
  set(token: string | null) {
    accessToken = token;
    listeners.forEach((l) => l(token));
  },
  subscribe(l: Listener): () => void {
    listeners.add(l);
    return () => void listeners.delete(l);
  },
};

// ---- device token: the shared shop-floor device's registration --------------------------------

export const deviceStore = {
  get(): string | null {
    try {
      return localStorage.getItem(DEVICE_KEY);
    } catch {
      return null;
    }
  },
  set(token: string | null) {
    try {
      if (token) localStorage.setItem(DEVICE_KEY, token);
      else localStorage.removeItem(DEVICE_KEY);
    } catch {
      /* storage unavailable */
    }
  },
};

function csrfToken(): string {
  const m = document.cookie.match(/(?:^|;\s*)fp_csrf=([^;]+)/);
  return m?.[1] ? decodeURIComponent(m[1]) : '';
}

async function toApiError(res: Response): Promise<ApiError> {
  try {
    const body = (await res.json()) as { error?: { code: string; message: string; details?: unknown } };
    if (body.error) return new ApiError(res.status, body.error.code, body.error.message, body.error.details);
  } catch {
    /* not JSON */
  }
  return new ApiError(res.status, 'http_' + res.status, res.statusText);
}

// ---- refresh: single flight so parallel 401s trigger one rotation ------------------------------

let refreshing: Promise<TokenOut | null> | null = null;

export function refreshSession(): Promise<TokenOut | null> {
  refreshing ??= (async () => {
    try {
      const res = await fetch(`${BASE}/auth/refresh`, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'X-CSRF-Token': csrfToken() },
      });
      if (!res.ok) {
        tokenStore.set(null);
        return null;
      }
      const out = (await res.json()) as TokenOut;
      tokenStore.set(out.access_token);
      return out;
    } catch {
      return null; // offline: keep whatever token we had
    } finally {
      refreshing = null;
    }
  })();
  return refreshing;
}

export interface RequestOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
  signal?: AbortSignal;
  device?: boolean; // send the device token
  idempotencyKey?: string;
}

export async function api<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const doFetch = () => {
    const headers: Record<string, string> = { Accept: 'application/json', ...opts.headers };
    if (opts.body !== undefined) headers['Content-Type'] = 'application/json';
    if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
    if (opts.device) headers['X-Device-Token'] = deviceStore.get() ?? '';
    if (opts.idempotencyKey) headers['Idempotency-Key'] = opts.idempotencyKey;
    return fetch(BASE + path, {
      method: opts.method ?? 'GET',
      headers,
      body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
      credentials: 'same-origin',
      signal: opts.signal,
    });
  };
  let res: Response;
  try {
    res = await doFetch();
    if (res.status === 401 && !path.startsWith('/auth/')) {
      const refreshed = await refreshSession();
      if (refreshed) res = await doFetch();
    }
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') throw e;
    throw new ApiError(0, 'network', 'Network error');
  }
  if (!res.ok) throw await toApiError(res);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export async function logoutRequest(): Promise<void> {
  try {
    await fetch(`${BASE}/auth/logout`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'X-CSRF-Token': csrfToken() },
    });
  } finally {
    tokenStore.set(null);
  }
}
