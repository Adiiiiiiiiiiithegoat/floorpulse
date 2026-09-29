import type { Page } from '@playwright/test';

export const DEMO_PASSWORD = 'FloorPulse!2026';
export const DEMO_PIN = '1234';
export const PUNE_DEVICE = 'demo-device-pun';

export async function loginAs(page: Page, email: string) {
  await page.goto('/login');
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill(DEMO_PASSWORD);
  await page.getByRole('button', { name: 'Sign in' }).click();
}

/** Registers the browser as the seeded Pune shop-floor device. */
export async function useDemoDevice(page: Page) {
  await page.addInitScript((token) => localStorage.setItem('fp_device_token', token), PUNE_DEVICE);
}

export async function pinLogin(page: Page, name: string, pin = DEMO_PIN) {
  await page.goto('/floor/login');
  await page.getByRole('button', { name }).click();
  for (const d of pin) await page.getByRole('button', { name: `Digit ${d}`, exact: true }).click();
}

export async function shot(page: Page, name: string) {
  await page.screenshot({ path: `e2e/__screens__/${name}.png`, fullPage: true });
}
