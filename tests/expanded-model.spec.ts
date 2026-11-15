import { test, expect } from '@playwright/test';
import catalog from './fixtures/expanded-catalog.json';
import comparison from './fixtures/expanded-comparison.json';
import fallow from './fixtures/expanded-fallow.json';

test.beforeEach(async ({ page }) => {
  await page.route('**/api/v1/catalog', route => route.fulfill({ json: catalog }));
  await page.route('**/api/v1/compare', route => route.fulfill({ json: comparison }));
});

test('expanded catalogue, model verdict, partial crops and evidence remain distinct', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('#location')).toBeEnabled();
  await expect(page.locator('#location option')).toHaveCount(22);
  await expect(page.locator('#main-crop option')).toHaveCount(30);
  await expect(page.locator('#prep-days')).toBeHidden();
  await expect(page.locator('.model-settings .schedule-settings')).toHaveCount(1);
  await page.getByRole('button', { name: 'See my options', exact: true }).click();
  await expect(page.locator('.crop-card')).toHaveCount(29);
  await expect(page.locator('.recommendation-crops')).toHaveText('Radish · Mungbean');
  await expect(page.getByRole('heading', { name: '197 days between harvest and your next planting', exact: true })).toBeVisible();
  await expect(page.locator('.result-window .model-context')).toContainText('Water supply: Rain only');
  await expect(page.locator('.filter-card .detail-switch')).toHaveCount(1);
  await expect(page.locator('.detail-toolbar, .about-section, .nav-about')).toHaveCount(0);
  await expect(page.locator('body')).not.toContainText('See the model’s condition scores, water gap, crop sources, and missing checks.');
  await expect(page.locator('body')).not.toContainText('Model order across all seasons');
  const mungRating = comparison.results.fields.rain.crops.mungbean.median_S.short.balanced;
  await expect(page.locator('[data-crop="mungbean"] .model-rating strong')).toHaveText(`${mungRating.toFixed(2)} / 1`);
  await expect.poll(() => page.locator('.crop-card').first().locator('.crop-photo img').evaluate((image: HTMLImageElement) => image.complete && image.naturalWidth > 0)).toBeTruthy();
  expect(await page.locator('.crop-photo').first().evaluate(el => el.getBoundingClientRect().width / el.parentElement!.clientWidth)).toBeGreaterThan(.99);
  for (const id of ['maize', 'sweetpotato']) {
    const card = page.locator(`[data-crop="${id}"]`);
    await expect(card.locator('.fit')).toHaveText('Partly checked');
    await expect(card).toContainText('Missing checks: Soil texture');
    await expect(card.locator('.recommendation-tag')).toHaveCount(0);
  }
  await page.getByRole('button', { name: 'More detailed', exact: true }).click();
  await expect(page.locator('[data-crop="tomato"]')).toContainText('DA guide caution');
  await expect(page.locator('[data-crop="maize"]')).toContainText('Same crop family');
  await expect(page.locator('[data-crop="mungbean"] .whole-schedule')).toContainText('50 days in total');
  await expect(page.locator('[data-crop="mungbean"] table tbody tr')).toHaveCount(comparison.results.planting_dates.mungbean.length);
  await expect(page.locator('[data-crop="mungbean"] .apa-references')).toContainText('Allen, R. G., Pereira, L. S., Raes, D., & Smith, M. (1998).');
  await expect(page.locator('[data-crop="mungbean"] .apa-references cite')).not.toHaveCount(0);
  await page.locator('[data-crop="mungbean"] .crop-references').screenshot({ path: 'test-results/crop-apa-references.png' });
  await page.getByRole('button', { name: 'Finishing early', exact: true }).click();
  await expect(page.locator('.active-filters')).toContainText('Finishing early');
  await expect(page.locator('.recommendation-crops')).toHaveText('Radish · Mungbean');
  await page.locator('.recommendation-notice').scrollIntoViewIfNeeded();
  await page.screenshot({ path: 'test-results/expanded-verdict.png' });
});

test('desktop workspace stays narrow and the floating sidebar scrolls without hiding reset', async ({ page }) => {
  await page.setViewportSize({ width: 1920, height: 640 });
  await page.goto('/');
  await expect(page.locator('#location')).toBeEnabled();
  const formWidth = await page.locator('#planner').evaluate(el => el.getBoundingClientRect().width);
  expect(formWidth).toBeLessThanOrEqual(1140);
  await page.getByRole('button', { name: 'See my options', exact: true }).click();
  await expect(page.locator('.crop-card')).toHaveCount(29);
  await page.locator('.crop-card').nth(8).scrollIntoViewIfNeeded();
  const reset = page.locator('.filter-reset').getByRole('button', { name: 'Start over', exact: true });
  await expect(reset).toBeInViewport({ ratio: 1 });
  const pane = page.locator('.filter-scroll');
  expect(await pane.evaluate(el => el.scrollHeight > el.clientHeight)).toBeTruthy();
  const pageScroll = await page.evaluate(() => scrollY);
  await pane.hover();
  await page.mouse.wheel(0, 450);
  await expect.poll(() => pane.evaluate(el => el.scrollTop)).toBeGreaterThan(0);
  expect(await page.evaluate(() => scrollY)).toBe(pageScroll);
  await expect(reset).toBeInViewport({ ratio: 1 });
  await page.screenshot({ path: 'test-results/compact-desktop-sidebar.png' });
  await reset.click();
  await expect(page.locator('#main-crop')).toHaveValue('rice');
  await expect(page.locator('.crop-card')).toHaveCount(0);
  await expect(page.locator('#prep-days')).toBeHidden();
});

test('fallow and all schedule allowances reach the model and none is an explicit result', async ({ page }) => {
  await page.route('**/api/v1/compare', route => route.fulfill({ json: fallow }));
  await page.goto('/');
  await expect(page.locator('#location')).toBeEnabled();
  await page.locator('#main-crop').selectOption('fallow');
  await expect(page.getByLabel('Field available from', { exact: true })).toHaveValue('2026-11-15');
  await page.getByText('Advanced settings', { exact: true }).click();
  await page.locator('#prep-days').fill('14');
  await page.locator('#picking-days').fill('21');
  await page.locator('#preparation').fill('7');
  await page.getByLabel('I have a soil test result', { exact: true }).check();
  await page.locator('#ph').fill('3');
  const request = page.waitForRequest('**/api/v1/compare');
  await page.getByRole('button', { name: 'See my options', exact: true }).click();
  expect((await request).postDataJSON()).toEqual(fallow.inputs);
  await expect(page.getByRole('heading', { name: 'No suitable recommendation', exact: true })).toBeVisible();
  await expect(page.locator('.recommendation-notice')).toContainText('Common limiting conditions: Soil pH');
  await expect(page.locator('.recommendation-tag')).toHaveCount(0);
  await expect(page.locator('.baseline')).toHaveCount(0);
  await expect(page.locator('[data-crop="mungbean"] .crop-time')).toContainText('105 days to spare');
  await page.getByRole('button', { name: 'More detailed', exact: true }).click();
  const plan = page.locator('[data-crop="mungbean"] .whole-schedule');
  await expect(plan).toContainText('92 days in total');
  await expect(plan).toContainText('14 days');
  await expect(plan).toContainText('21 days');
  await expect(plan).toContainText('7 days');
  await page.getByRole('button', { name: 'Edit field details', exact: true }).click();
  await expect(page.locator('#prep-days')).toHaveValue('14');
  await expect(page.locator('#picking-days')).toHaveValue('21');
  await page.getByRole('button', { name: 'Tagalog', exact: true }).click();
  await expect(page.getByLabel('Paghahanda / pahinga bago magtanim', { exact: true })).toHaveValue('14');
});

test('phone schedule validation and results fit without horizontal page overflow', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/');
  await expect(page.locator('#location')).toBeEnabled();
  await page.getByText('Advanced settings', { exact: true }).click();
  await page.locator('#picking-days').fill('181');
  await page.getByRole('button', { name: 'See my options', exact: true }).click();
  await expect(page.locator('.form-error')).toContainText('picking days from 0 to 180');
  await expect(page.locator('.crop-card')).toHaveCount(0);
  await page.locator('#picking-days').fill('0');
  await page.getByRole('button', { name: 'See my options', exact: true }).click();
  await expect(page.locator('.crop-card')).toHaveCount(29);
  await page.getByRole('button', { name: 'More detailed', exact: true }).click();
  await page.locator('[data-crop="maize"] .fit').scrollIntoViewIfNeeded();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await page.screenshot({ path: 'test-results/expanded-phone.png' });
});
