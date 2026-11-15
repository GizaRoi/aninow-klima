import { test, expect } from '@playwright/test';
import { messages } from '../apps/web/lib/messages';
import type { Comparison, ModelInputs } from '../apps/web/lib/model';

test('live Render service calculates a comparison through the browser', async ({ page }) => {
  test.skip(process.env.KLIMA_LIVE_TEST !== '1', 'Opt in to requests against the deployed Render service.');
  test.setTimeout(240_000);
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(process.env.KLIMA_FRONTEND_URL || '/');
  await expect(page.locator('#location')).toBeEnabled({ timeout: 190_000 });
  const cropCount = await page.locator('#main-crop option').count();
  expect(cropCount).toBeGreaterThan(0);
  const responsePromise = page.waitForResponse(response => response.url().endsWith('/api/v1/compare') && response.request().method() === 'POST', { timeout: 190_000 });
  await page.getByRole('button', { name: 'See my options', exact: true }).click();
  const response = await responsePromise;
  expect(response.status()).toBe(200);
  const body = await response.json();
  expect(body.mode).toBe('rules_model');
  expect(body.contract_version).toBe('klima-comparison.v1');
  await expect(page.locator('.crop-card')).toHaveCount(cropCount);
  await expect(page.locator('.crop-card').first()).toHaveAttribute('data-crop', body.ranking[0]);
  const counts = body.results.fields.rain.crops.mungbean.counts.balanced.all.short;
  await expect(page.locator('[data-crop="mungbean"]')).toContainText(`${counts.pass} of ${counts.of}`);
  await expect(page.locator('body')).not.toContainText(/prototype|sample results|not connected|interactive demo/i);
  await page.screenshot({ path: 'test-results/live-render-results.png', fullPage: true });
  expect(errors).toEqual([]);
});

test('live custom parameters and drainage edits match the request, model response and crop cards', async ({ page }) => {
  test.skip(process.env.KLIMA_LIVE_TEST !== '1', 'Opt in to requests against the deployed Render service.');
  test.setTimeout(480_000);
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto(process.env.KLIMA_FRONTEND_URL || '/');
  await expect(page.locator('#location')).toBeEnabled({ timeout: 190_000 });
  await page.locator('#location').selectOption('Batac, Ilocos Norte');
  await page.locator('#main-crop').selectOption('tomato');
  await page.locator('#harvest').fill('2026-06-01');
  await page.locator('#next').fill('2026-09-30');
  await page.getByRole('group', { name: 'Where does the water come from?', exact: true }).getByRole('button', { name: 'Irrigation', exact: true }).click();
  await page.getByLabel('I have a soil test result', { exact: true }).check();
  await page.locator('#ph').fill('6.4');
  await page.locator('#soil-texture').selectOption('medium');
  await page.getByText('Advanced settings', { exact: true }).click();
  await page.locator('#preparation').fill('9');
  await page.locator('#pass-mark').fill('0.65');

  for (const drainage of ['poorly_drained', 'well_drained'] as const) {
    await page.getByRole('group', { name: 'Does water stay on the field for days after rain?', exact: true }).getByRole('button', { name: drainage === 'poorly_drained' ? 'Yes' : 'No', exact: true }).click();
    await page.getByRole('button', { name: 'Finishing early', exact: true }).click();
    const expected: ModelInputs = {
      place: 'Batac, Ilocos Norte', main_crop: 'tomato', harvest: '2026-06-01', next_planting: '2026-09-30',
      water: 'irrigation', drainage, soil_ph: 6.4, soil_texture: 'medium', turnaround_days: 9, pass_mark: 0.65, priority: 'finishing_early',
    };
    const responsePromise = page.waitForResponse(response => response.url().endsWith('/api/v1/compare') && response.request().method() === 'POST', { timeout: 190_000 });
    await page.getByRole('button', { name: 'See my options', exact: true }).click();
    const response = await responsePromise;
    expect(response.request().postDataJSON()).toEqual(expected);
    expect(response.status()).toBe(200);
    const body: Comparison = await response.json();
    expect(body.inputs).toEqual(expected);
    expect(body.results.meta).toMatchObject({ main_crop: 'tomato', pass_mark: 0.65, turnaround_days: 9, window_days: 121 });
    expect(body.results.soil).toMatchObject({ ph: 6.4, texture: 'medium' });
    const field = body.results.fields.irrigation;
    expect(body.ranking).toEqual(field.rankings.finishing_early);
    await expect(page.getByRole('heading', { name: 'Your options', exact: true })).toBeVisible();
    expect(await page.locator('.crop-card:not(.crop-excluded)').evaluateAll(cards => cards.map(card => card.getAttribute('data-crop')))).toEqual(body.ranking);
    await expect(page.locator('.model-context')).toContainText('Water supply: Irrigation');
    await expect(page.locator('.model-context')).toContainText(messages('en').drainageAnswers[drainage]);
    for (const [id, crop] of Object.entries(field.crops)) {
      const card = page.locator(`[data-crop="${id}"]`);
      const counts = crop.counts.balanced.all.short;
      await expect(card.locator('.crop-history')).toContainText(`${counts.pass} of ${counts.of}`);
      await expect(card.locator('.crop-time')).toContainText(`${121 - crop.scored_days.short - 9} days to spare`);
      if (crop.median_deficit_mm.short !== null) {
        const gap = new Intl.NumberFormat('en-PH', { maximumFractionDigits: 0 }).format(crop.median_deficit_mm.short);
        await expect(card.locator('.model-fact')).toContainText(`${gap} mm`);
      }
    }
    for (const [id, reasons] of Object.entries(field.excluded)) {
      await expect(page.locator(`[data-crop="${id}"]`)).toHaveClass(/crop-excluded/);
      for (const reason of reasons) await expect(page.locator(`[data-crop="${id}"] .exclusion`)).toContainText(messages('en').reasons[reason as keyof ReturnType<typeof messages>['reasons']]);
    }
    if (drainage === 'poorly_drained') {
      expect(field.excluded.mungbean).toContain('needs_well_drained_soil');
    } else {
      expect(field.excluded.mungbean).toBeUndefined();
      await expect(page.locator('[data-crop="mungbean"]')).not.toHaveClass(/crop-excluded/);
      await expect(page.locator('.exclusion').filter({ hasText: 'You answered that water stays' })).toHaveCount(0);
    }
    await page.getByRole('button', { name: 'Dry season', exact: true }).click();
    await page.getByRole('button', { name: 'Saving water', exact: true }).click();
    expect(await page.locator('.crop-card:not(.crop-excluded)').evaluateAll(cards => cards.map(card => card.getAttribute('data-crop')))).toEqual(field.rankings.saving_water);
    for (const [id, crop] of Object.entries(field.crops)) {
      const counts = crop.counts.balanced.dry.short;
      await expect(page.locator(`[data-crop="${id}"] .crop-history`)).toContainText(counts.of > 0 ? `${counts.pass} of ${counts.of}` : messages('en').noHistory);
    }
    console.log(JSON.stringify({ verified_inputs: body.inputs, ranked: body.ranking, excluded: field.excluded }));
    if (drainage === 'poorly_drained') {
      await page.getByRole('button', { name: 'All seasons', exact: true }).click();
      await page.getByRole('button', { name: 'Edit field details', exact: true }).click();
    }
  }
  expect(errors).toEqual([]);
});
