import { describe, expect, it } from 'vitest';
import en from './locales/en.json';
import hi from './locales/hi.json';

function keys(obj: object, prefix = ''): string[] {
  return Object.entries(obj).flatMap(([k, v]) =>
    typeof v === 'object' && v !== null ? keys(v as object, `${prefix}${k}.`) : [`${prefix}${k}`],
  );
}

function placeholders(s: string): string[] {
  return [...s.matchAll(/{{\s*(\w+)\s*}}/g)].map((m) => m[1]!).sort();
}

describe('translations', () => {
  it('hi has exactly the same keys as en', () => {
    expect(keys(hi).sort()).toEqual(keys(en).sort());
  });

  it('interpolation placeholders match', () => {
    const get = (o: object, path: string) =>
      path.split('.').reduce<unknown>((acc, k) => (acc as Record<string, unknown>)[k], o) as string;
    for (const k of keys(en)) expect(placeholders(get(hi, k)), k).toEqual(placeholders(get(en, k)));
  });
});
