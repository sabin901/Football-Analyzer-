const { test, expect } = require('@playwright/test');
test('Every public view renders without JavaScript errors or missing assets', async ({ page }) => {
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('response', (r) => {
    if (r.status() >= 400) errors.push(`${r.status()} ${r.url()}`);
  });
  for (const view of [
    'overview',
    'matches',
    'compare',
    'players',
    'matchlab',
    'events',
    'heatmap',
    'forecast',
    'coverage',
    'analyst',
  ]) {
    await page.goto(`/#view=${view}&league=PD&season=2026-27`);
    await expect(page.locator('#content')).toHaveAttribute('aria-busy', 'false');
    await expect(page.locator('#content')).not.toContainText('Loading');
    await expect(page.locator('#page-title')).not.toBeEmpty();
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1),
    ).toBeTruthy();
  }
  expect(errors).toEqual([]);
});
test('Private evidence import, note, save and backup remain local', async ({ page }) => {
  const outgoing = [];
  page.on('request', (r) => {
    if (!r.url().startsWith('http://127.0.0.1:8770') && !r.url().startsWith('blob:'))
      outgoing.push(r.url());
  });
  await page.goto('/#view=analyst');
  await page.getByRole('button', { name: 'Try a synthetic example' }).click();
  await expect(page.locator('#content')).toContainText('Synthetic demo.');
  await page.getByRole('button', { name: 'Use event', exact: true }).first().click();
  await page
    .getByLabel('Observation · what happened?')
    .fill('<img src=x onerror=alert(1)> is untrusted source text.');
  await page
    .getByLabel('Interpretation · what might explain it?')
    .fill('A test observation; not a real club conclusion.');
  await page.getByLabel('Recommendation · what should change?').fill('Review the original video.');
  await page.getByLabel('Limitations and counterevidence').fill('Synthetic data only.');
  await page.getByRole('button', { name: 'Add evidence note', exact: true }).click();
  await expect(page.locator('.analyst-notes article')).toHaveCount(2);
  await expect(page.locator('.analyst-notes img')).toHaveCount(0);
  await page.getByRole('button', { name: 'Save on this device', exact: true }).click();
  await page.reload();
  await expect(page.locator('.analyst-notes article')).toHaveCount(2);
  const downloaded = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Export project backup', exact: true }).click();
  expect((await downloaded).suggestedFilename()).toBe('footlyzer-project.json');
  expect(outgoing).toEqual([]);
});
test('Malformed CSV is rejected without replacing the current project', async ({ page }) => {
  await page.goto('/#view=analyst');
  await page.getByLabel('Match / project title').fill('Keep my project');
  await page.locator('#analysis-csv').setInputFiles({
    name: 'bad.csv',
    mimeType: 'text/csv',
    buffer: Buffer.from('id,period\nbad,99'),
  });
  await expect(page.locator('#analyst-status')).toContainText('exact columns');
  await expect(page.getByLabel('Match / project title')).toHaveValue('Keep my project');
});
test('Mobile overview and evidence workspace have no page overflow', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  for (const view of ['overview', 'compare', 'events', 'heatmap', 'forecast', 'analyst']) {
    await page.goto(`/#view=${view}&league=PL&season=2026-27`);
    await expect(page.locator('#content')).toHaveAttribute('aria-busy', 'false');
    await expect(page.locator('#content')).not.toContainText('Loading');
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1),
    ).toBeTruthy();
  }
});

test('Local video metadata and evidence seeking work without an upload', async ({ page }) => {
  await page.goto('/#view=analyst');
  await page.getByRole('button', { name: 'Try a synthetic example', exact: true }).click();
  await page.locator('#analysis-video-file').setInputFiles('tests/fixtures/synthetic-video.mp4');
  await expect
    .poll(() => page.locator('#analysis-video').evaluate((v) => v.duration))
    .toBeGreaterThan(120);
  await page.getByRole('button', { name: 'Use event', exact: true }).first().click();
  await expect.poll(() => page.locator('#analysis-video').evaluate((v) => v.currentTime)).toBe(120);
  await expect(page.locator('#note-evidence')).toHaveValue('demo-1');
});

for (const width of [320, 600, 768, 1024, 1920]) {
  test(`All workspaces reflow at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    for (const view of [
      'overview',
      'matches',
      'compare',
      'players',
      'matchlab',
      'events',
      'heatmap',
      'forecast',
      'coverage',
      'analyst',
    ]) {
      await page.goto(`/#view=${view}&league=PL&season=2026-27`);
      await expect(page.locator('#content')).toHaveAttribute('aria-busy', 'false');
      await expect(page.locator('#content')).not.toContainText('Loading');
      await expect(page.locator('#view-guide summary')).toBeVisible();
      expect(
        await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1),
      ).toBeTruthy();
    }
  });
}
test('Guided historical comparison and forecast explorer use actual archive examples', async ({
  page,
}) => {
  await page.goto('/#view=compare&league=PD&season=2026-27');
  await expect(page.locator('#content')).toHaveAttribute('aria-busy', 'false');
  await page.locator('#view-guide summary').click();
  await page.getByRole('button', { name: 'Compare two historical teams' }).click();
  await expect(page.getByLabel('Season', { exact: true })).toHaveValue('2017-18');
  await expect(page.locator('.comparison-team .team-emblem')).toHaveCount(2);
  await page.goto('/#view=forecast&league=PD');
  await expect(page.locator('#content')).toHaveAttribute('aria-busy', 'false');
  await expect(page.getByLabel('Historical fixture example')).toBeVisible();
  await page.getByLabel('Historical fixture example').selectOption({ index: 1 });
  await page.getByText('Explore scorelines & model disagreement', { exact: true }).first().click();
  await expect(page.locator('.score-cells').first()).toBeVisible();
  expect(
    await page
      .locator('.forecast-fixture > div:first-child')
      .first()
      .evaluate((el) => el.getBoundingClientRect().width),
  ).toBeGreaterThan(200);
  expect(
    await page
      .locator('.score-explorer')
      .first()
      .evaluate((el) => el.getBoundingClientRect().width),
  ).toBeGreaterThan(500);
  await expect(page.locator('.replay-label')).toContainText('NOT A LIVE PREDICTION');
});
