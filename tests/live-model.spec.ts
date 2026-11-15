import { test, expect } from '@playwright/test';

test('live Render service calculates a comparison through the browser', async ({ page }) => {
  test.skip(process.env.KLIMA_LIVE_TEST !== '1', 'Opt in to requests against the deployed Render service.');
  test.setTimeout(240_000);
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(process.env.KLIMA_FRONTEND_URL || '/');
  await expect(page.locator('#location option')).toHaveCount(7, { timeout: 190_000 });
  const responsePromise = page.waitForResponse(response => response.url().endsWith('/api/v1/compare') && response.request().method() === 'POST', { timeout: 190_000 });
  await page.getByRole('button', { name: 'See my options', exact: true }).click();
  const response = await responsePromise;
  expect(response.status()).toBe(200);
  const body = await response.json();
  expect(body.mode).toBe('rules_model');
  expect(body.contract_version).toBe('klima-comparison.v1');
  await expect(page.locator('.crop-card')).toHaveCount(10);
  await expect(page.locator('.crop-card').first()).toHaveAttribute('data-crop', body.ranking[0]);
  const counts = body.results.fields.rain.crops.mungbean.counts.balanced.all.short;
  await expect(page.locator('[data-crop="mungbean"]')).toContainText(`${counts.pass} of ${counts.of}`);
  await expect(page.locator('body')).not.toContainText(/prototype|sample results|not connected|interactive demo/i);
  await page.screenshot({ path: 'test-results/live-render-results.png', fullPage: true });
  expect(errors).toEqual([]);
});
