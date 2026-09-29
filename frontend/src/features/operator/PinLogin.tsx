import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Navigate, useNavigate, useSearchParams } from 'react-router';
import { PinPad } from '@/components/PinPad';
import { Button, EmptyState, ErrorBanner, PageLoader, errorMessage } from '@/components/ui';
import { LanguageSwitcher } from '@/components/Prefs';
import { api, ApiError, deviceStore, type Schemas } from '@/lib/api';
import { useAuth } from '@/lib/auth';

const LAST_USER_KEY = 'fp_last_operator';

function lastUser(): number | null {
  try {
    const v = localStorage.getItem(LAST_USER_KEY);
    return v ? Number(v) : null;
  } catch {
    return null;
  }
}

export function PinLogin() {
  const { t } = useTranslation();
  const { state, loginPin } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const hasDevice = !!deviceStore.get();
  const [picked, setPicked] = useState<number | null>(lastUser);
  const [pin, setPin] = useState('');
  const [search, setSearch] = useState('');
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  const device = useQuery({
    queryKey: ['device-info'],
    queryFn: () => api<Schemas['DeviceInfoOut']>('/auth/device', { device: true }),
    enabled: hasDevice,
    retry: false,
  });

  const operators = useMemo(() => device.data?.operators ?? [], [device.data]);
  const current = operators.find((o) => o.id === picked);
  const filtered = operators.filter((o) => o.name.toLowerCase().includes(search.toLowerCase()));

  useEffect(() => {
    if (device.error instanceof ApiError && device.error.code === 'device_required') deviceStore.set(null);
  }, [device.error]);

  if (!hasDevice || (device.error instanceof ApiError && device.error.code === 'device_required'))
    return <Navigate to="/floor/setup" replace />;
  if (state.status === 'authed') return <Navigate to="/floor" replace />;
  if (device.isLoading) return <PageLoader />;

  const submit = async (value: string) => {
    if (!current || busy) return;
    setBusy(true);
    setError(null);
    try {
      await loginPin(current.id, value);
      try {
        localStorage.setItem(LAST_USER_KEY, String(current.id));
      } catch {
        /* ignore */
      }
      navigate('/floor', { replace: true });
    } catch (e) {
      setError(
        e instanceof ApiError && e.code === 'invalid_credentials' ? new ApiError(401, 'wrong_pin', '') : e,
      );
      setPin('');
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col gap-5 p-4">
      <header className="flex items-center justify-between">
        <div>
          <p className="text-sm font-bold text-accent">{t('common.appName')}</p>
          <p className="text-sm text-muted">{device.data?.site_name}</p>
        </div>
        <LanguageSwitcher />
      </header>
      {params.get('locked') && <p className="rounded-lg bg-panel-2 p-3 text-center">{t('floor.locked')}</p>}
      <ErrorBanner error={device.error} onRetry={() => void device.refetch()} />

      {current ? (
        <section className="flex flex-1 flex-col items-center gap-6">
          <h1 className="text-center text-2xl font-bold">{t('floor.pinFor', { name: current.name })}</h1>
          {error ? (
            <p role="alert" className="text-center font-semibold text-danger">
              {errorMessage(error, t)}
            </p>
          ) : null}
          <PinPad
            value={pin}
            onChange={setPin}
            onSubmit={(v) => void submit(v)}
            disabled={busy}
            minLength={current.pin_length ?? 4}
            maxLength={current.pin_length ?? 6}
          />
          <Button
            variant="ghost"
            size="lg"
            onClick={() => {
              setPicked(null);
              setPin('');
              setError(null);
            }}
          >
            {t('floor.switchUser')}
          </Button>
        </section>
      ) : (
        <section className="flex flex-col gap-3">
          <h1 className="text-2xl font-bold">{t('floor.whoAreYou')}</h1>
          {operators.length > 8 && (
            <input
              type="search"
              placeholder={t('floor.searchName')}
              aria-label={t('floor.searchName')}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="min-h-12 rounded-lg border border-border bg-panel px-3 text-base"
            />
          )}
          {operators.length === 0 ? (
            <EmptyState title={t('floor.noOperators')} />
          ) : (
            <ul className="grid grid-cols-2 gap-3">
              {filtered.map((o) => (
                <li key={o.id}>
                  <button
                    type="button"
                    onClick={() => setPicked(o.id)}
                    className="flex min-h-20 w-full flex-col items-start justify-center rounded-xl border border-border bg-panel p-3 text-start active:bg-panel-2"
                  >
                    <span className="text-lg font-semibold">{o.name}</span>
                    {o.employee_code && <span className="text-sm text-muted">{o.employee_code}</span>}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      )}
    </main>
  );
}
