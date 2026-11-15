import { test, expect } from '@playwright/test';
import catalog from './fixtures/catalog.json';
import comparison from './fixtures/comparison.json';

test.beforeEach(async ({ page }) => {
  await page.route('**/api/v1/catalog', route => route.fulfill({ json: catalog }));
  await page.route('**/api/v1/compare', route => route.fulfill({ json: comparison }));
});

test('model flow, historical filters, API order, explanations and real download', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/');
  await expect(page.getByLabel('Location', { exact: true })).toBeEnabled();
  await expect(page.locator('#location option')).toHaveCount(7);
  await expect(page.locator('#main-crop option')).toHaveCount(10);
  await expect(page.locator('body')).not.toContainText(/prototype|sample results|not connected|interactive demo/i);
  const request = page.waitForRequest('**/api/v1/compare');
  await page.getByRole('button', { name: 'See my options', exact: true }).click();
  expect((await request).postDataJSON()).toEqual(comparison.inputs);
  await expect(page.getByRole('heading', { name: 'Your options', exact: true })).toBeVisible();
  await expect(page.locator('.crop-card')).toHaveCount(10);
  await expect(page.locator('.fit-out')).toHaveCount(3);
  await expect(page.locator('.crop-card').first()).toHaveAttribute('data-crop', 'mungbean');
  const mung = page.locator('[data-crop="mungbean"]');
  await expect(mung).toContainText('22 of 41');
  await page.getByRole('button', { name: 'More detailed', exact: true }).click();
  await expect(page.locator('.crop-details[open]')).toHaveCount(7);
  await expect(mung).toContainText('FAO');
  await page.getByRole('button', { name: 'Dry season', exact: true }).click();
  const history = comparison.results.fields.rain.crops.mungbean.counts.balanced.dry.short;
  await expect(mung).toContainText(`${history.pass} of ${history.of} past dry seasons`);
  await page.getByRole('button', { name: 'Finishing early', exact: true }).click();
  expect(await page.locator('.crop-card:not(.crop-excluded)').evaluateAll(cards => cards.map(c => c.getAttribute('data-crop')))).toEqual(comparison.results.fields.rain.rankings.finishing_early);
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Download comparison', exact: true }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe('aninow-model-comparison.json');
  const stream = await download.createReadStream();
  const chunks: Buffer[] = [];
  for await (const chunk of stream!) chunks.push(chunk);
  const saved = JSON.parse(Buffer.concat(chunks).toString());
  expect(saved.mode).toBe('rules_model');
  expect(saved.model_version).toBe(comparison.model_version);
  expect(saved.display).toEqual({ season: 'dry', priority: 'finishing_early' });
  await page.screenshot({ path: 'test-results/desktop-results.png', fullPage: true });
  expect(errors).toEqual([]);
});

test('date validation, measured inputs, language preservation and API payload', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('#location')).toBeEnabled();
  await page.locator('#next').fill('2026-11-01');
  await page.getByRole('button', { name: 'See my options', exact: true }).click();
  await expect(page.locator('.form-error')).toContainText('must be after');
  await page.locator('#next').fill('2027-05-31');
  await page.locator('#main-crop').selectOption('mungbean');
  await page.getByLabel('I have a soil test result', { exact: true }).check();
  await page.locator('#ph').fill('6.3');
  await page.locator('#soil-texture').selectOption('heavy');
  await page.getByText('Advanced settings', { exact: true }).click();
  await page.locator('#preparation').fill('12');
  await page.locator('#pass-mark').fill('0.7');
  await page.getByRole('button', { name: 'Tagalog', exact: true }).click();
  await expect(page.locator('#ph')).toHaveValue('6.3');
  await expect(page.locator('html')).toHaveAttribute('lang', 'tl');
  const request = page.waitForRequest('**/api/v1/compare');
  await page.getByRole('button', { name: 'Tingnan ang mga pagpipilian', exact: true }).click();
  expect((await request).postDataJSON()).toMatchObject({ main_crop: 'mungbean', soil_ph: 6.3, soil_texture: 'heavy', turnaround_days: 12, pass_mark: 0.7 });
  await page.getByRole('button', { name: 'English', exact: true }).click();
  await page.getByRole('button', { name: 'Edit field details', exact: true }).click();
  await expect(page.locator('#ph')).toHaveValue('6.3');
  await page.getByLabel('I have a soil test result', { exact: true }).uncheck();
  const blank = page.waitForRequest('**/api/v1/compare');
  await page.getByRole('button', { name: 'See my options', exact: true }).click();
  expect((await blank).postDataJSON()).toMatchObject({ soil_ph: null, soil_texture: null });
});

test('service failure preserves inputs, exposes retry and never shows sample cards', async ({ page }) => {
  let attempts = 0;
  await page.route('**/api/v1/compare', route => ++attempts === 1
    ? route.fulfill({ status: 503, json: { error: { message: 'busy', field_errors: {} }, request_id: 'busy-request' } })
    : route.fulfill({ json: comparison }));
  await page.goto('/');
  await expect(page.locator('#location')).toBeEnabled();
  await page.locator('#location').selectOption('Batac, Ilocos Norte');
  await page.getByRole('button', { name: 'See my options', exact: true }).click();
  await expect(page.locator('.form-error')).toContainText('busy or unavailable');
  await expect(page.locator('#location')).toHaveValue('Batac, Ilocos Norte');
  await expect(page.locator('.crop-card')).toHaveCount(0);
  await page.getByRole('button', { name: 'Try again', exact: true }).click();
  await expect(page.locator('.crop-card')).toHaveCount(10);
});

test('catalogue failure can be retried and submit stays disabled', async ({ page }) => {
  let attempts = 0;
  await page.route('**/api/v1/catalog', route => ++attempts === 1
    ? route.fulfill({ status: 502, contentType: 'text/html', body: '<html>Waking</html>' })
    : route.fulfill({ json: catalog }));
  await page.goto('/');
  await expect(page.locator('.form-error')).toContainText('could not be reached');
  await expect(page.locator('button[type="submit"]')).toBeDisabled();
  await page.getByRole('button', { name: 'Try again', exact: true }).first().click();
  await expect(page.locator('button[type="submit"]')).toBeEnabled();
});

test('all crops excluded stays a valid result without manufactured scores', async ({ page }) => {
  const blocked = structuredClone(comparison);
  const field = blocked.results.fields.rain;
  field.crops = {} as typeof field.crops;
  for (const key of Object.keys(field.rankings) as (keyof typeof field.rankings)[]) field.rankings[key] = [];
  field.excluded = Object.fromEntries(catalog.crops.map(crop => [crop.id, ['does_not_fit_window']])) as typeof field.excluded;
  blocked.ranking = [];
  await page.route('**/api/v1/compare', route => route.fulfill({ json: blocked }));
  await page.goto('/');
  await page.getByRole('button', { name: 'See my options', exact: true }).click();
  await expect(page.locator('.fit-out')).toHaveCount(10);
  await expect(page.locator('.crop-history')).toHaveCount(0);
});

test('phone Tagalog form and model results fit the screen', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await page.getByRole('button', { name: 'Tagalog', exact: true }).click();
  await page.screenshot({ path: 'test-results/mobile-form.png', fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.getByRole('button', { name: 'Tingnan ang mga pagpipilian', exact: true }).click();
  await expect(page.locator('.crop-card')).toHaveCount(10);
  await page.getByRole('button', { name: 'Panahon ng El Niño', exact: true }).click();
  await page.getByRole('button', { name: 'Mas detalyado', exact: true }).click();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await expect(page.locator('body')).not.toContainText(/halimbawang resulta|hindi pa nakakonekta|demo lamang/i);
  await page.screenshot({ path: 'test-results/mobile-results.png', fullPage: true });
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('lang', 'tl');
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
