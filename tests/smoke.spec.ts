import { expect, test } from '@playwright/test';

test('home board loads and Contacts opens with no console errors', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (err) => {
    errors.push(`pageerror: ${err.message}`);
  });
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      errors.push(`console: ${msg.text()}`);
    }
  });

  await page.goto('/');
  await expect(page).toHaveTitle(/MixYard/);
  await expect(page.getByRole('heading', { name: "Today's board" })).toBeVisible();
  await expect(page.getByText('Specialty Concrete · Kelso yard')).toBeVisible();

  await page.getByRole('button', { name: 'Contacts', exact: true }).click();
  await expect(page).toHaveURL(/#\/contacts$/);
  await expect(page.getByRole('heading', { name: 'Contacts' })).toBeVisible();
  await expect(page.getByText('Dana Ellison')).toBeVisible();

  expect(errors, errors.join('\n')).toEqual([]);
});
