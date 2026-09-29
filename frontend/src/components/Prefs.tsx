import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { LANGUAGES, setLanguage } from '@/i18n';

type Theme = 'light' | 'dark';

function readTheme(key: string, fallback: Theme): Theme {
  try {
    const v = localStorage.getItem(key);
    return v === 'light' || v === 'dark' ? v : fallback;
  } catch {
    return fallback;
  }
}

/** Each app keeps its own theme: the operator app defaults to dark (glare), the manager app to the OS setting. */
export function useTheme(scope: 'floor' | 'app') {
  const key = `fp_theme_${scope}`;
  const fallback: Theme =
    scope === 'floor' || window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  const [theme, setTheme] = useState<Theme>(() => readTheme(key, fallback));
  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark');
    const meta = document.querySelector('meta[name="theme-color"]');
    meta?.setAttribute('content', theme === 'dark' ? '#0b1220' : '#f5f7fa');
    try {
      localStorage.setItem(key, theme);
    } catch {
      /* ignore */
    }
  }, [theme, key]);
  return [theme, setTheme] as const;
}

export function ThemeToggle({ theme, onChange }: { theme: Theme; onChange(t: Theme): void }) {
  const { t } = useTranslation();
  const next = theme === 'dark' ? 'light' : 'dark';
  return (
    <button
      type="button"
      onClick={() => onChange(next)}
      className="flex min-h-11 min-w-11 items-center justify-center rounded-lg text-xl hover:bg-panel-2"
      aria-label={`${t('common.theme')}: ${next === 'dark' ? t('common.themeDark') : t('common.themeLight')}`}
      title={t('common.theme')}
    >
      <span aria-hidden>{theme === 'dark' ? '☀' : '☾'}</span>
    </button>
  );
}

export function LanguageSwitcher() {
  const { t, i18n } = useTranslation();
  return (
    <label className="flex items-center">
      <span className="sr-only">{t('common.language')}</span>
      <select
        value={i18n.language}
        onChange={(e) => setLanguage(e.target.value)}
        className="min-h-11 rounded-lg border border-border bg-panel px-2 text-sm text-fg"
      >
        {LANGUAGES.map((l) => (
          <option key={l.code} value={l.code}>
            {l.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export function OnlineBadge() {
  const { t } = useTranslation();
  const [online, setOnline] = useState(navigator.onLine);
  useEffect(() => {
    const up = () => setOnline(true);
    const down = () => setOnline(false);
    window.addEventListener('online', up);
    window.addEventListener('offline', down);
    return () => {
      window.removeEventListener('online', up);
      window.removeEventListener('offline', down);
    };
  }, []);
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${
        online ? 'bg-running text-white' : 'bg-stopped text-white'
      }`}
      role="status"
    >
      <span aria-hidden className="size-2 rounded-full bg-white" />
      {online ? t('common.online') : t('common.offline')}
    </span>
  );
}
