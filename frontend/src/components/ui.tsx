import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from 'react';
import { forwardRef, useId } from 'react';
import { useTranslation } from 'react-i18next';
import { ApiError } from '@/lib/api';

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost';

const VARIANTS: Record<Variant, string> = {
  primary: 'bg-accent text-accent-fg hover:opacity-90',
  secondary: 'bg-panel-2 text-fg border border-border hover:bg-panel',
  danger: 'bg-stopped text-white hover:opacity-90',
  ghost: 'text-fg hover:bg-panel-2',
};

export function cx(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(' ');
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: 'md' | 'lg';
  busy?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'primary', size = 'md', busy, className, disabled, children, ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      className={cx(
        'inline-flex items-center justify-center gap-2 rounded-lg font-semibold transition disabled:opacity-50',
        size === 'lg' ? 'min-h-touch px-5 text-lg' : 'min-h-11 px-4 text-sm',
        VARIANTS[variant],
        className,
      )}
      disabled={disabled || busy}
      aria-busy={busy || undefined}
      {...rest}
    >
      {busy && <Spinner small />}
      {children}
    </button>
  );
});

interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
}

export const Field = forwardRef<HTMLInputElement, FieldProps>(function Field(
  { label, error, className, id, ...rest },
  ref,
) {
  const autoId = useId();
  const inputId = id ?? autoId;
  return (
    <div className={cx('flex flex-col gap-1', className)}>
      <label htmlFor={inputId} className="text-sm font-medium text-muted">
        {label}
      </label>
      <input
        ref={ref}
        id={inputId}
        aria-invalid={!!error || undefined}
        aria-describedby={error ? `${inputId}-err` : undefined}
        className="min-h-12 rounded-lg border border-border bg-panel px-3 text-base text-fg"
        {...rest}
      />
      {error && (
        <p id={`${inputId}-err`} className="text-sm text-danger">
          {error}
        </p>
      )}
    </div>
  );
});

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  children: ReactNode;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { label, className, id, children, ...rest },
  ref,
) {
  const autoId = useId();
  const selectId = id ?? autoId;
  return (
    <div className={cx('flex flex-col gap-1', className)}>
      <label htmlFor={selectId} className="text-sm font-medium text-muted">
        {label}
      </label>
      <select
        ref={ref}
        id={selectId}
        className="min-h-12 rounded-lg border border-border bg-panel px-3 text-base text-fg"
        {...rest}
      >
        {children}
      </select>
    </div>
  );
});

export function Spinner({ small }: { small?: boolean }) {
  const { t } = useTranslation();
  return (
    <span
      role="status"
      aria-label={t('common.loading')}
      className={cx(
        'inline-block animate-spin rounded-full border-2 border-current border-t-transparent',
        small ? 'size-4' : 'size-8',
      )}
    />
  );
}

export function PageLoader() {
  return (
    <div className="flex min-h-[50vh] items-center justify-center text-muted">
      <Spinner />
    </div>
  );
}

export function errorMessage(err: unknown, t: (k: string) => string): string {
  if (err instanceof ApiError) {
    const key = `errors.${err.code}`;
    const msg = t(key);
    return msg === key ? err.message || t('errors.generic') : msg;
  }
  return t('errors.generic');
}

export function ErrorBanner({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const { t } = useTranslation();
  if (!error) return null;
  return (
    <div
      role="alert"
      className="flex items-center justify-between gap-3 rounded-lg border border-stopped/50 bg-stopped/10 p-3 text-sm"
    >
      <span>{errorMessage(error, t)}</span>
      {onRetry && (
        <Button variant="secondary" onClick={onRetry}>
          {t('common.retry')}
        </Button>
      )}
    </div>
  );
}

export function EmptyState({ title, help, action }: { title: string; help?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-xl border border-dashed border-border p-8 text-center">
      <p className="text-lg font-semibold">{title}</p>
      {help && <p className="max-w-md text-muted">{help}</p>}
      {action}
    </div>
  );
}

export function Card({
  title,
  children,
  className,
}: {
  title?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={cx('rounded-xl border border-border bg-panel p-4', className)}>
      {title && <h2 className="mb-3 text-base font-semibold">{title}</h2>}
      {children}
    </section>
  );
}
