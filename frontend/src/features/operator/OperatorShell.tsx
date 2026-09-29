import { useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Outlet, useNavigate } from 'react-router';
import { LanguageSwitcher, OnlineBadge, ThemeToggle } from '@/components/Prefs';
import { Button } from '@/components/ui';
import { api, type Schemas } from '@/lib/api';
import { useAuth } from '@/lib/auth';

/** Signs the operator out after inactivity; the PIN screen then pre-selects them for a quick unlock. */
function useIdleLock(minutes: number, onLock: () => void) {
  const timer = useRef<number | undefined>(undefined);
  const callback = useRef(onLock);
  useEffect(() => {
    callback.current = onLock;
  });
  useEffect(() => {
    const reset = () => {
      window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => callback.current(), minutes * 60_000);
    };
    const events = ['pointerdown', 'keydown', 'scroll', 'visibilitychange'] as const;
    events.forEach((e) => window.addEventListener(e, reset, { passive: true }));
    reset();
    return () => {
      window.clearTimeout(timer.current);
      events.forEach((e) => window.removeEventListener(e, reset));
    };
  }, [minutes]);
}

export function OperatorShell({
  theme,
  onTheme,
}: {
  theme: 'light' | 'dark';
  onTheme(t: 'light' | 'dark'): void;
}) {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const settings = useQuery({
    queryKey: ['org-settings'],
    queryFn: () => api<Schemas['OrgSettings']>('/org/settings'),
    staleTime: 10 * 60_000,
  });

  useIdleLock(
    settings.data?.operator_idle_lock_min ?? 10,
    () => void logout().then(() => navigate('/floor/login?locked=1', { replace: true })),
  );

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-10 flex items-center gap-2 border-b border-border bg-panel px-3 py-2">
        <div className="min-w-0 flex-1">
          <p className="truncate text-base font-bold">{user?.name}</p>
          <OnlineBadge />
        </div>
        <LanguageSwitcher />
        <ThemeToggle theme={theme} onChange={onTheme} />
        <Button variant="secondary" onClick={() => void logout().then(() => navigate('/floor/login'))}>
          {t('floor.switchUser')}
        </Button>
      </header>
      <main className="flex-1 p-3">
        <Outlet />
      </main>
    </div>
  );
}
