import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useTranslation } from 'react-i18next';
import { Link, Navigate, useLocation, useNavigate } from 'react-router';
import { Button, ErrorBanner, Field, PageLoader } from '@/components/ui';
import { LanguageSwitcher, ThemeToggle, useTheme } from '@/components/Prefs';
import { ApiError } from '@/lib/api';
import { landingPath, useAuth } from '@/lib/auth';

const schema = z.object({
  email: z.string().min(1),
  password: z.string().min(1),
  totp: z.string().optional(),
});
type Form = z.infer<typeof schema>;

export default function LoginPage() {
  const { t } = useTranslation();
  const { state, loginPassword } = useAuth();
  const [theme, setTheme] = useTheme('app');
  const navigate = useNavigate();
  const location = useLocation();
  const [error, setError] = useState<unknown>(null);
  const [needTotp, setNeedTotp] = useState(false);
  const { register, handleSubmit, formState } = useForm<Form>({ resolver: zodResolver(schema) });

  if (state.status === 'loading') return <PageLoader />;
  if (state.status === 'authed') return <Navigate to={landingPath(state.user)} replace />;

  const onSubmit = async (f: Form) => {
    setError(null);
    try {
      const user = await loginPassword(f.email, f.password, f.totp);
      const from = (location.state as { from?: string } | null)?.from;
      navigate(from && from.startsWith('/app') ? from : landingPath(user), { replace: true });
    } catch (e) {
      if (e instanceof ApiError && e.code === 'totp_required') setNeedTotp(true);
      setError(e);
    }
  };

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 p-4">
      <div className="absolute end-4 top-4 flex items-center gap-2">
        <LanguageSwitcher />
        <ThemeToggle theme={theme} onChange={setTheme} />
      </div>
      <div className="w-full max-w-sm rounded-2xl border border-border bg-panel p-6 shadow-sm">
        <p className="mb-1 text-sm font-bold tracking-wide text-accent">{t('common.appName')}</p>
        <h1 className="mb-6 text-2xl font-bold">{t('auth.title')}</h1>
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4" noValidate>
          <Field
            label={t('auth.email')}
            type="email"
            autoComplete="username"
            error={formState.errors.email && t('common.required')}
            {...register('email')}
          />
          <Field
            label={t('auth.password')}
            type="password"
            autoComplete="current-password"
            error={formState.errors.password && t('common.required')}
            {...register('password')}
          />
          {needTotp && (
            <Field
              label={t('auth.totpCode')}
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              autoFocus
              {...register('totp')}
            />
          )}
          <ErrorBanner error={error} />
          <Button type="submit" size="lg" busy={formState.isSubmitting}>
            {formState.isSubmitting ? t('auth.signingIn') : t('auth.signIn')}
          </Button>
        </form>
      </div>
      <Link to="/floor" className="min-h-11 content-center text-accent underline">
        {t('auth.shopFloorLink')}
      </Link>
    </main>
  );
}
