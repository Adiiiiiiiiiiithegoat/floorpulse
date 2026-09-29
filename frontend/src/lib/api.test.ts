import { afterEach, describe, expect, it, vi } from 'vitest';
import { api, ApiError, tokenStore } from './api';

function json(status: number, body: unknown) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

afterEach(() => {
  vi.restoreAllMocks();
  tokenStore.set(null);
});

describe('api client', () => {
  it('maps the error envelope to ApiError', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      json(409, { error: { code: 'conflict', message: 'dup' } }),
    );
    await expect(api('/sites')).rejects.toMatchObject({ status: 409, code: 'conflict' });
  });

  it('refreshes once for parallel 401s and retries', async () => {
    tokenStore.set('old');
    let refreshCalls = 0;
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith('/auth/refresh')) {
        refreshCalls++;
        return json(200, { access_token: 'new', user: {} });
      }
      const auth = (init?.headers as Record<string, string>).Authorization;
      return auth === 'Bearer new'
        ? json(200, { ok: true })
        : json(401, { error: { code: 'token_expired', message: '' } });
    });
    const results = await Promise.all([api('/a'), api('/b'), api('/c')]);
    expect(results).toEqual([{ ok: true }, { ok: true }, { ok: true }]);
    expect(refreshCalls).toBe(1);
    expect(tokenStore.get()).toBe('new');
  });

  it('reports network failures as code "network"', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Failed to fetch'));
    const err = await api('/x').catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).code).toBe('network');
  });
});
