import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import en from './locales/en.json';
import hi from './locales/hi.json';

/** Adding a language: drop `locales/<code>.json` in, then add it here. RTL languages go in RTL too. */
export const LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'hi', label: 'हिन्दी' },
] as const;
const RTL = new Set(['ar', 'ur', 'he', 'fa']);
const STORAGE_KEY = 'fp_lang';

function storedLanguage(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function applyDocumentLanguage(lng: string): void {
  document.documentElement.lang = lng;
  document.documentElement.dir = RTL.has(lng) ? 'rtl' : 'ltr';
}

export function setLanguage(lng: string): void {
  try {
    localStorage.setItem(STORAGE_KEY, lng);
  } catch {
    /* storage unavailable: language just won't persist */
  }
  void i18n.changeLanguage(lng);
}

void i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, hi: { translation: hi } },
  lng: storedLanguage() ?? (navigator.language.startsWith('hi') ? 'hi' : 'en'),
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
  returnNull: false,
});

applyDocumentLanguage(i18n.language);
i18n.on('languageChanged', applyDocumentLanguage);

export default i18n;
