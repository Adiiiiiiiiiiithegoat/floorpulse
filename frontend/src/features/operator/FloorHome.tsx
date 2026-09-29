import { useTranslation } from 'react-i18next';
import { EmptyState } from '@/components/ui';

export function FloorHome() {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-bold">{t('floor.home')}</h1>
      <EmptyState title={t('floor.machinesEmpty')} help={t('floor.machinesEmptyHelp')} />
    </div>
  );
}
