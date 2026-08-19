import { expect, test } from '@playwright/test';

test('dashboard filters, quality evidence, and AI answer work together', async ({ page }) => {
  await page.goto('/');

  await expect(page.getByRole('heading', { name: '店务罗盘' })).toBeVisible();
  await expect(page.getByLabel(/净营业额：¥/)).toBeVisible();

  await page.getByLabel('选择门店').selectOption('S01');
  await page.getByRole('button', { name: '应用筛选' }).click();
  await expect(page.getByText(/S01/).first()).toBeVisible();

  await page.getByRole('button', { name: /数据质量/ }).click();
  await expect(page.getByRole('dialog', { name: '数据质量说明' })).toBeVisible();
  await expect(page.getByText('安全修复')).toBeVisible();
  await page.getByRole('button', { name: '关闭', exact: true }).click();

  const streamResponse = page.waitForResponse((response) => (
    response.url().endsWith('/api/v1/chat/stream')
    && response.request().method() === 'POST'
  ));
  await page.getByRole('button', { name: '牛肉poke 六月卖了多少钱？' }).click();
  await expect.poll(async () => (await streamResponse).headers()['content-type']).toContain('text/event-stream');
  await expect(page.getByText(/牛肉poke在 2026-06-01 至 2026-06-30/)).toBeVisible();
  await page.getByText('1 条可核验证据').click();
  await expect(page.getByText('get_revenue')).toBeVisible();
  await page.getByRole('button', { name: '应用到看板' }).click();

  await expect(page.getByLabel('开始日期')).toHaveValue('2026-06-01');
  await expect(page.getByLabel('结束日期')).toHaveValue('2026-06-30');
});
