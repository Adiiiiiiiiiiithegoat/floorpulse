import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Button, Card, ErrorBanner, PageLoader } from '@/components/ui';
import { api, type Schemas } from '@/lib/api';
import { useAuth } from '@/lib/auth';

export function Account() {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const qc = useQueryClient();
  const sessions = useQuery({
    queryKey: ['me', 'sessions'],
    queryFn: () => api<Schemas['SessionOut'][]>('/me/sessions'),
  });
  const revoke = useMutation({
    mutationFn: (id: string) => api(`/me/sessions/${id}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['me', 'sessions'] }),
  });
  const fmt = new Intl.DateTimeFormat(i18n.language, { dateStyle: 'medium', timeStyle: 'short' });

  if (!user) return <PageLoader />;
  return (
    <div className="flex max-w-3xl flex-col gap-4">
      <h1 className="text-2xl font-bold">{t('account.title')}</h1>
      <Card title={t('account.profile')}>
        <dl className="grid grid-cols-[max-content_1fr] gap-x-6 gap-y-2 text-sm">
          <dt className="text-muted">{t('auth.email')}</dt>
          <dd>{user.email}</dd>
          <dt className="text-muted">{t('account.roles')}</dt>
          <dd>{user.roles.map((r) => t(`roles.${r}`)).join(', ')}</dd>
          <dt className="text-muted">{t('account.twoFactor')}</dt>
          <dd>{user.totp_enabled ? t('account.twoFactorOn') : t('account.twoFactorOff')}</dd>
        </dl>
      </Card>
      <Card title={t('account.sessions')}>
        <p className="mb-3 text-sm text-muted">{t('account.sessionsHelp')}</p>
        <ErrorBanner error={sessions.error ?? revoke.error} onRetry={() => void sessions.refetch()} />
        {sessions.isLoading ? (
          <PageLoader />
        ) : (
          <ul className="divide-y divide-border">
            {sessions.data?.map((s) => (
              <li key={s.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                <div className="min-w-0">
                  <p className="truncate font-medium">
                    {s.user_agent ?? '—'}{' '}
                    {s.current && (
                      <span className="ms-2 rounded bg-accent px-2 py-0.5 text-xs text-accent-fg">
                        {t('account.thisDevice')}
                      </span>
                    )}
                  </p>
                  <p className="text-sm text-muted">
                    {t('account.signedInVia', { method: t(`account.method_${s.auth_method}`) })} ·{' '}
                    {t('account.lastActive', { when: fmt.format(new Date(s.last_used_at ?? s.created_at)) })}
                  </p>
                </div>
                {!s.current && (
                  <Button
                    variant="secondary"
                    onClick={() => revoke.mutate(s.id)}
                    busy={revoke.isPending && revoke.variables === s.id}
                  >
                    {t('account.revoke')}
                  </Button>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
