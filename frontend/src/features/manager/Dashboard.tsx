import { useTranslation } from 'react-i18next';
import { EmptyState } from '@/components/ui';

export function Dashboard() {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-bold">{t('manager.dashboardTitle')}</h1>
      <EmptyState title={t('manager.dashboardEmpty')} />
    </div>
  );
}
