import { expect, test } from '@playwright/test';
import { loginAs, pinLogin, shot, useDemoDevice } from './helpers';

test('@desktop manager signs in and sees the dashboard and account', async ({ page }) => {
  await page.goto('/login');
  await shot(page, 'p0-login-desktop');
  await loginAs(page, 'manager@demo.floorpulse.app');
  await expect(page.getByRole('heading', { name: 'Plant overview' })).toBeVisible();
  await shot(page, 'p0-dashboard-desktop');
  await page.getByRole('link', { name: 'My account' }).click();
  await expect(page.getByText('This device')).toBeVisible();
  await shot(page, 'p0-account-desktop');
});

test('@desktop wrong password shows a friendly error', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email').fill('manager@demo.floorpulse.app');
  await page.getByLabel('Password').fill('nope');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('alert')).toContainText('Wrong email or password');
});

test('@desktop every staff role can sign in', async ({ page }) => {
  for (const email of [
    'admin@demo.floorpulse.app',
    'supervisor.pune@demo.floorpulse.app',
    'tech@demo.floorpulse.app',
    'quality@demo.floorpulse.app',
    'stores@demo.floorpulse.app',
  ]) {
    await loginAs(page, email);
    await expect(page.getByRole('heading', { name: 'Plant overview' })).toBeVisible();
    await page.getByRole('button', { name: 'Sign out' }).click();
    await expect(page.getByRole('heading', { name: 'Sign in to FloorPulse' })).toBeVisible();
  }
});

test('@mobile operator signs in with a PIN on a registered device', async ({ page }) => {
  await useDemoDevice(page);
  await page.goto('/floor/login');
  await expect(page.getByRole('heading', { name: 'Who are you?' })).toBeVisible();
  await shot(page, 'p0-operator-picker-390');
  await page.getByRole('button', { name: /Ganesh Jadhav/ }).click();
  await shot(page, 'p0-operator-pin-390');
  for (const d of '1234') await page.getByRole('button', { name: `Digit ${d}`, exact: true }).click();
  await expect(page.getByRole('heading', { name: 'My machines' })).toBeVisible();
  await shot(page, 'p0-operator-home-390');
  // Session survives a reload (refresh cookie)
  await page.reload();
  await expect(page.getByRole('heading', { name: 'My machines' })).toBeVisible();
});

test('@mobile wrong PIN is rejected', async ({ page }) => {
  await useDemoDevice(page);
  await pinLogin(page, 'Lakshmi Rao E102', '9999');
  await expect(page.getByRole('alert')).toContainText('Wrong PIN');
});

test('@mobile unregistered device goes to setup, supervisor registers it', async ({ page }) => {
  await page.goto('/floor');
  await expect(page.getByRole('heading', { name: 'Set up this device' })).toBeVisible();
  await page.getByLabel('Email').fill('supervisor.pune@demo.floorpulse.app');
  await page.getByLabel('Password').fill('FloorPulse!2026');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await page.getByLabel('Device name').fill('Machining tablet');
  await shot(page, 'p0-device-setup-390');
  await page.getByRole('button', { name: 'Register device' }).click();
  await expect(page.getByRole('heading', { name: 'Who are you?' })).toBeVisible();
});

test('@mobile Hindi language switch', async ({ page }) => {
  await useDemoDevice(page);
  await page.goto('/floor/login');
  await page.getByRole('combobox', { name: 'Language' }).selectOption('hi');
  await expect(page.getByRole('heading', { name: 'आप कौन हैं?' })).toBeVisible();
  await shot(page, 'p0-operator-picker-hi-390');
});
