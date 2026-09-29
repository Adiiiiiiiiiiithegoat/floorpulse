import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router';
import { Button, ErrorBanner, Field, Select } from '@/components/ui';
import { api, deviceStore, logoutRequest, tokenStore, type Schemas, type TokenOut } from '@/lib/api';

type Site = Schemas['SiteOut'];
type Area = Schemas['AreaOut'];

/** A supervisor registers this phone/tablet once. Their session ends as soon as the device is registered. */
export function DeviceSetup() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [step, setStep] = useState<'login' | 'pick'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [sites, setSites] = useState<Site[]>([]);
  const [areas, setAreas] = useState<Area[]>([]);
  const [siteId, setSiteId] = useState<number | null>(null);
  const [areaId, setAreaId] = useState<number | null>(null);
  const [name, setName] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  };

  const login = () =>
    run(async () => {
      const out = await api<TokenOut>('/auth/login', { method: 'POST', body: { email, password } });
      tokenStore.set(out.access_token);
      const [s, a] = await Promise.all([api<Site[]>('/sites'), api<Area[]>('/areas')]);
      setSites(s);
      setAreas(a);
      setSiteId(s[0]?.id ?? null);
      setStep('pick');
    });

  const registerDevice = () =>
    run(async () => {
      if (siteId === null) return;
      const out = await api<Schemas['DeviceRegisterOut']>('/devices', {
        method: 'POST',
        body: { name: name || 'Shop-floor device', site_id: siteId, area_id: areaId },
      });
      deviceStore.set(out.device_token);
      await logoutRequest();
      navigate('/floor/login', { replace: true });
    });

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-5 p-4">
      <h1 className="text-2xl font-bold">{t('floor.setupTitle')}</h1>
      <p className="text-muted">{t('floor.setupHelp')}</p>
      {step === 'login' ? (
        <form
          className="flex flex-col gap-4"
          onSubmit={(e) => {
            e.preventDefault();
            void login();
          }}
        >
          <Field
            label={t('auth.email')}
            type="email"
            autoComplete="username"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <Field
            label={t('auth.password')}
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <ErrorBanner error={error} />
          <Button type="submit" size="lg" busy={busy}>
            {t('auth.signIn')}
          </Button>
        </form>
      ) : (
        <form
          className="flex flex-col gap-4"
          onSubmit={(e) => {
            e.preventDefault();
            void registerDevice();
          }}
        >
          <Field
            label={t('floor.deviceName')}
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={120}
          />
          <Select
            label={t('floor.site')}
            value={siteId ?? ''}
            onChange={(e) => setSiteId(Number(e.target.value))}
          >
            {sites.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </Select>
          <Select
            label={t('floor.line')}
            value={areaId ?? ''}
            onChange={(e) => setAreaId(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">{t('floor.anyLine')}</option>
            {areas
              .filter((a) => a.site_id === siteId)
              .map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
          </Select>
          <ErrorBanner error={error} />
          <Button type="submit" size="lg" busy={busy} disabled={siteId === null}>
            {t('floor.register')}
          </Button>
        </form>
      )}
    </main>
  );
}
