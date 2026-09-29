import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { NavLink, Outlet, useNavigate } from 'react-router';
import { LanguageSwitcher, ThemeToggle, useTheme } from '@/components/Prefs';
import { Button, cx } from '@/components/ui';
import { useAuth } from '@/lib/auth';

const NAV = [
  { to: '/app', key: 'manager.nav.dashboard', end: true },
  { to: '/app/account', key: 'manager.nav.account', end: false },
];

export function ManagerShell() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [theme, setTheme] = useTheme('app');
  const [open, setOpen] = useState(false);

  const nav = (
    <nav aria-label="Main" className="flex flex-col gap-1 p-3">
      {NAV.map((n) => (
        <NavLink
          key={n.to}
          to={n.to}
          end={n.end}
          onClick={() => setOpen(false)}
          className={({ isActive }) =>
            cx(
              'flex min-h-11 items-center rounded-lg px-3 font-medium',
              isActive ? 'bg-accent text-accent-fg' : 'text-fg hover:bg-panel-2',
            )
          }
        >
          {t(n.key)}
        </NavLink>
      ))}
    </nav>
  );

  return (
    <div className="flex min-h-screen">
      <aside className="hidden w-60 shrink-0 border-e border-border bg-panel lg:block">
        <p className="px-6 pt-5 text-lg font-bold text-accent">{t('common.appName')}</p>
        <p className="truncate px-6 text-xs text-muted">{user?.organization_name}</p>
        {nav}
      </aside>
      {open && (
        <div
          className="fixed inset-0 z-30 lg:hidden"
          role="dialog"
          aria-modal="true"
          aria-label={t('common.menu')}
        >
          <button
            type="button"
            className="absolute inset-0 bg-black/50"
            aria-label={t('common.close')}
            onClick={() => setOpen(false)}
          />
          <aside className="relative h-full w-64 bg-panel">{nav}</aside>
        </div>
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex items-center gap-2 border-b border-border bg-panel px-4 py-2">
          <button
            type="button"
            className="flex min-h-11 min-w-11 items-center justify-center rounded-lg text-xl hover:bg-panel-2 lg:hidden"
            aria-label={t('common.menu')}
            aria-expanded={open}
            onClick={() => setOpen(true)}
          >
            <span aria-hidden>☰</span>
          </button>
          <p className="flex-1 truncate text-sm text-muted">{t('manager.welcome', { name: user?.name })}</p>
          <LanguageSwitcher />
          <ThemeToggle theme={theme} onChange={setTheme} />
          <Button variant="secondary" onClick={() => void logout().then(() => navigate('/login'))}>
            {t('common.signOut')}
          </Button>
        </header>
        <main className="flex-1 p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
