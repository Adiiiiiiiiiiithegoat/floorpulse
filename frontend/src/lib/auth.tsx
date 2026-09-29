import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { api, logoutRequest, refreshSession, tokenStore, type Me, type TokenOut } from './api';
import { setLanguage } from '@/i18n';

export type Role =
  'operator' | 'supervisor' | 'technician' | 'inspector' | 'storekeeper' | 'manager' | 'admin';

type AuthState = { status: 'loading' } | { status: 'anon' } | { status: 'authed'; user: Me };

interface AuthApi {
  state: AuthState;
  user: Me | null;
  loginPassword(email: string, password: string, totpCode?: string): Promise<Me>;
  loginPin(userId: number, pin: string): Promise<Me>;
  logout(): Promise<void>;
}

const AuthContext = createContext<AuthApi | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ status: 'loading' });
  const qc = useQueryClient();

  const accept = useCallback((out: TokenOut) => {
    tokenStore.set(out.access_token);
    if (out.user.language) setLanguage(out.user.language);
    setState({ status: 'authed', user: out.user });
    return out.user;
  }, []);

  useEffect(() => {
    // Restore the session from the refresh cookie on boot.
    void refreshSession().then((out) => (out ? accept(out) : setState({ status: 'anon' })));
    return tokenStore.subscribe((token) => {
      if (token === null) setState((s) => (s.status === 'authed' ? { status: 'anon' } : s));
    });
  }, [accept]);

  const value = useMemo<AuthApi>(
    () => ({
      state,
      user: state.status === 'authed' ? state.user : null,
      loginPassword: async (email, password, totpCode) =>
        accept(
          await api<TokenOut>('/auth/login', {
            method: 'POST',
            body: { email, password, totp_code: totpCode || null },
          }),
        ),
      loginPin: async (userId, pin) =>
        accept(
          await api<TokenOut>('/auth/pin-login', {
            method: 'POST',
            body: { user_id: userId, pin },
            device: true,
          }),
        ),
      logout: async () => {
        await logoutRequest();
        qc.clear();
        setState({ status: 'anon' });
      },
    }),
    [state, accept, qc],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthApi {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth outside AuthProvider');
  return ctx;
}

export function hasRole(user: Me | null, ...roles: Role[]): boolean {
  if (!user) return false;
  return user.roles.includes('admin') || roles.some((r) => user.roles.includes(r));
}

/** Operator-only users land on the shop-floor app, everyone else on the manager app. */
export function landingPath(user: Me): string {
  const managerish = user.roles.some((r) => r !== 'operator');
  return managerish ? '/app' : '/floor';
}
