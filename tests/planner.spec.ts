import { test, expect } from '@playwright/test';

test('field-to-results flow, filters, explanations, editing, and download', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toContainText('after rice');
  await page.getByRole('button', { name: 'Plan my next planting', exact: true }).click();
  await expect(page.getByLabel('Location', { exact: true })).toBeDisabled();
  await page.getByRole('button', { name: 'See my options', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Your options', exact: true })).toBeVisible();
  await expect(page.getByText('Your field is free for 197 days')).toBeVisible();
  await expect(page.locator('.crop-card')).toHaveCount(4);
  const mung = page.locator('[data-crop="mung"]');
  await expect(mung).toContainText('36 of 44');
  await mung.getByText('Show why', { exact: true }).click();
  await expect(mung.getByText('Soil pH (no soil test)', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Dry season', exact: true }).click();
  await expect(mung).toContainText('6 of 9 past dry seasons');
  await page.getByRole('button', { name: 'Saving water', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Saving water', exact: true })).toHaveAttribute('aria-pressed', 'true');
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download comparison', exact: true }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe('aninow-sample-comparison.json');
  await page.getByRole('button', { name: 'Edit field details', exact: true }).click();
  await page.getByRole('button', { name: 'Yes', exact: true }).click();
  await page.getByRole('button', { name: 'See my options', exact: true }).click();
  await expect(page.locator('.fit-out')).toHaveCount(3);
  await page.screenshot({ path: 'test-results/desktop-results.png', fullPage: true });
  expect(errors).toEqual([]);
});

test('validation blocks invalid windows and unknown soil stays unscored', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel('Next rice planting', { exact: true }).fill('2026-11-01');
  await page.getByRole('button', { name: 'See my options', exact: true }).click();
  await expect(page.locator('.form-error')).toContainText('must be after');
  await page.getByLabel('Next rice planting', { exact: true }).fill('2027-05-31');
  await page.getByLabel('Soil type', { exact: true }).selectOption('');
  await page.getByRole('button', { name: 'Not sure', exact: true }).click();
  await page.getByRole('button', { name: 'See my options', exact: true }).click();
  await page.locator('[data-crop="mung"]').getByText('Show why', { exact: true }).click();
  await expect(page.locator('[data-crop="mung"] .drainage-warning')).toBeVisible();
  await expect(page.locator('[data-crop="mung"] .details-body').getByText('Soil type', { exact: true })).toBeVisible();
});

test('language switching preserves values and results and persists after reload', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel('Soil pH', { exact: false }).fill('6.3');
  await page.getByRole('button', { name: 'Tagalog', exact: true }).click();
  await expect(page.locator('html')).toHaveAttribute('lang', 'tl');
  await expect(page.locator('#ph')).toHaveValue('6.3');
  await page.getByRole('button', { name: 'Tingnan ang mga pagpipilian', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Mga pagpipilian mo', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'English', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Your options', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Edit field details', exact: true }).click();
  await expect(page.locator('#ph')).toHaveValue('6.3');
  await page.getByRole('button', { name: 'Tagalog', exact: true }).click();
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('lang', 'tl');
});

test('phone layout and Tagalog results fit within the viewport', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await page.getByRole('button', { name: 'Tagalog', exact: true }).click();
  await page.screenshot({ path: 'test-results/mobile-form.png', fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.getByRole('button', { name: 'Buksan ang menu', exact: true }).click();
  await expect(page.locator('nav.nav-open')).toBeVisible();
  await page.locator('nav').getByRole('button', { name: 'Planuhin ang susunod na tanim', exact: true }).click();
  await page.getByRole('button', { name: 'Tingnan ang mga pagpipilian', exact: true }).click();
  await expect(page.locator('.crop-card')).toHaveCount(4);
  await page.getByRole('button', { name: 'Panahon ng El Niño', exact: true }).click();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: 'test-results/mobile-results.png', fullPage: true });
});

test('more detailed opens the HTML explanations and preserves mode across filters and language', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'See my options', exact: true }).click();
  await expect(page.locator('.crop-details[open]')).toHaveCount(0);
  await page.getByRole('button', { name: 'More detailed', exact: true }).click();
  await expect(page.locator('.crop-details[open]')).toHaveCount(4);
  const mung = page.locator('[data-crop="mung"]');
  await expect(mung.getByRole('heading', { name: 'Why', exact: true })).toBeVisible();
  await expect(mung.getByRole('heading', { name: 'For your soil', exact: true })).toBeVisible();
  await expect(mung.getByRole('heading', { name: 'We could not check', exact: true })).toBeVisible();
  await expect(mung.getByRole('heading', { name: 'Ask your agriculturist first', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Dry season', exact: true }).click();
  await page.getByRole('button', { name: 'Saving water', exact: true }).click();
  await expect(page.locator('.crop-details[open]')).toHaveCount(4);
  await page.getByRole('button', { name: 'Tagalog', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Mas detalyado', exact: true })).toHaveAttribute('aria-pressed', 'true');
  await expect(mung.getByRole('heading', { name: 'Hindi namin nasuri', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Simple', exact: true }).click();
  await expect(page.locator('.crop-details[open]')).toHaveCount(0);
  await mung.getByText('Ipakita kung bakit', { exact: true }).click();
  await expect(mung.locator('details')).toHaveAttribute('open', '');
});

test('team route shows full portraits with accessible names and no duplicate name captions', async ({ page }) => {
  await page.goto('/');
  await page.locator('nav').getByRole('link', { name: 'Our team', exact: true }).click();
  await expect(page).toHaveURL(/\/team\/$/);
  await expect(page.getByRole('heading', { level: 1, name: 'Our team', exact: true })).toBeVisible();
  await expect(page.locator('.team-card img')).toHaveCount(4);
  await expect(page.locator('.team-card').filter({ hasText: /\S/ })).toHaveCount(0);
  await expect(page.locator('nav a[aria-current="page"]')).toHaveText('Our team');
  await expect.poll(() => page.locator('.team-card img').evaluateAll(images => images.every(image => (image as HTMLImageElement).complete && (image as HTMLImageElement).naturalWidth > 0))).toBe(true);
  await page.screenshot({ path: 'test-results/desktop-team.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole('button', { name: 'Tagalog', exact: true }).click();
  await expect(page.getByRole('heading', { level: 1, name: 'Ang aming koponan', exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.screenshot({ path: 'test-results/mobile-team.png', fullPage: true });
  await page.getByRole('link', { name: 'Bumalik sa pagpaplano ng tanim', exact: true }).click();
  await expect(page).toHaveURL(/\/#planner$/);
  await expect(page.locator('html')).toHaveAttribute('lang', 'tl');
});
