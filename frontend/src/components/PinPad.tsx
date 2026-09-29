import { useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { cx } from './ui';

interface Props {
  value: string;
  onChange(v: string): void;
  onSubmit(v: string): void;
  maxLength?: number;
  minLength?: number;
  disabled?: boolean;
}

/** Big-button PIN pad for gloved hands. Physical keyboards work too. Auto-submits at max length. */
export function PinPad({ value, onChange, onSubmit, maxLength = 6, minLength = 4, disabled }: Props) {
  const { t } = useTranslation();

  const press = (d: string) => {
    if (disabled || value.length >= maxLength) return;
    const next = value + d;
    onChange(next);
    if (next.length === maxLength) onSubmit(next);
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (/^\d$/.test(e.key)) press(e.key);
      else if (e.key === 'Backspace') onChange(value.slice(0, -1));
      else if (e.key === 'Enter' && value.length >= minLength) onSubmit(value);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  });

  const key =
    'flex min-h-touch min-w-touch items-center justify-center rounded-xl bg-panel-2 text-2xl font-bold active:bg-border disabled:opacity-40';

  return (
    <div className="flex w-full flex-col items-center gap-5">
      <div className="flex gap-3" aria-live="polite" aria-label={`${value.length} / ${maxLength}`}>
        {Array.from({ length: maxLength }, (_, i) => (
          <span
            key={i}
            className={cx(
              'size-4 rounded-full border-2 border-fg',
              i < value.length && 'bg-fg',
              i >= minLength && i >= value.length && 'opacity-40',
            )}
          />
        ))}
      </div>
      <div className="grid w-full max-w-xs grid-cols-3 gap-3">
        {['1', '2', '3', '4', '5', '6', '7', '8', '9'].map((d) => (
          <button
            key={d}
            type="button"
            className={key}
            onClick={() => press(d)}
            disabled={disabled}
            aria-label={t('floor.digit', { d })}
          >
            {d}
          </button>
        ))}
        <button
          type="button"
          className={cx(key, 'text-base')}
          onClick={() => onChange('')}
          disabled={disabled}
        >
          {t('floor.clearPin')}
        </button>
        <button
          type="button"
          className={key}
          onClick={() => press('0')}
          disabled={disabled}
          aria-label={t('floor.digit', { d: 0 })}
        >
          0
        </button>
        <button
          type="button"
          className={key}
          onClick={() => (value.length >= minLength ? onSubmit(value) : onChange(value.slice(0, -1)))}
          disabled={disabled}
          aria-label={value.length >= minLength ? t('common.confirm') : t('floor.deletePin')}
        >
          {value.length >= minLength ? '✓' : '⌫'}
        </button>
      </div>
    </div>
  );
}
