import { test, expect } from '@playwright/test';
import catalog from './fixtures/catalog.json';

test('welcome finishes in about two seconds even when the catalogue is still loading', async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.clock.install({ time: new Date('2026-11-15T08:00:00Z') });
  await page.clock.pauseAt(new Date('2026-11-15T08:00:00Z'));
  let releaseCatalog!: () => void;
  const waiting = new Promise<void>(resolve => { releaseCatalog = resolve; });
  await page.route('**/api/v1/catalog', async route => { await waiting; await route.fulfill({ json: catalog }); });
  await page.goto('/');
  const intro = page.locator('.app-intro');
  await expect(intro).toBeVisible();
  await expect(intro.getByRole('img', { name: 'AniNow Klima' })).toBeVisible();
  await expect.poll(() => page.locator('.intro-landscape').evaluate((image: HTMLImageElement) => image.complete && image.naturalWidth > 0)).toBe(true);
  await page.keyboard.press('Tab');
  expect(await page.evaluate(() => document.activeElement === document.body)).toBe(true);
  await page.clock.runFor(1700);
  await expect(intro).toBeVisible();
  await page.screenshot({ path: 'test-results/desktop-intro.png' });
  await page.clock.runFor(500);
  await expect(intro).toHaveCount(0);
  await expect(page.getByRole('status')).toContainText('Loading');
  await expect(page.locator('#location')).toBeDisabled();
  await page.keyboard.press('Tab');
  await expect(page.locator('.skip-link')).toBeFocused();
  releaseCatalog();
  await expect(page.locator('#location')).toBeEnabled();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('What can you plant after rice?');
  await expect(page.locator('#location')).toBeInViewport({ ratio: 1 });
  await expect(page.locator('#main-crop')).toBeInViewport({ ratio: 1 });
  expect(await page.evaluate(() => window.scrollY)).toBe(0);
  await page.locator('.skip-link').blur();
  await page.screenshot({ path: 'test-results/desktop-opening.png' });
  await page.getByRole('button', { name: 'Tagalog', exact: true }).click();
  await expect(intro).toHaveCount(0);
});

for (const viewport of [{ width: 768, height: 1024 }, { width: 390, height: 844 }, { width: 360, height: 740 }]) {
  test(`opening has readable controls above the fold at ${viewport.width}px`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.route('**/api/v1/catalog', route => route.fulfill({ json: catalog }));
    await page.goto('/');
    await expect(page.locator('.app-intro')).toBeVisible();
    expect(await page.locator('.intro-landscape').evaluate(image => getComputedStyle(image).animationName)).toBe('none');
    if (viewport.width === 390) await page.screenshot({ path: 'test-results/mobile-intro.png' });
    await expect(page.locator('.app-intro')).toHaveCount(0);
    await expect(page.locator('#location')).toBeEnabled();
    await expect(page.locator('#location')).toBeInViewport({ ratio: 1 });
    expect(await page.locator('#location').evaluate(input => parseFloat(getComputedStyle(input).fontSize))).toBeGreaterThanOrEqual(16);
    expect(await page.evaluate(() => window.scrollY === 0 && document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: `test-results/mobile-opening-${viewport.width}.png` });
    await page.getByRole('button', { name: 'Tagalog', exact: true }).click();
    await expect(page.getByRole('heading', { level: 1 })).toContainText('pagkatapos ng palay?');
    await expect(page.locator('#location')).toBeInViewport({ ratio: 1 });
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  });
}
