import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, expect, test, vi } from 'vitest';

import { api } from '../../api/client';
import type { ChatResponse } from '../../api/types';
import { AiAssistant } from './AiAssistant';

vi.mock('../../api/client', () => ({ api: { ask: vi.fn() } }));

const response: ChatResponse = {
  answer: '牛肉poke 6月净营业额为 ¥12,345.67。',
  status: 'answered',
  mode: 'mock',
  evidence: [
    {
      tool: 'get_revenue',
      parameters: { product_name: '牛肉poke', start_date: '2026-06-01', end_date: '2026-06-30' },
      result: { revenue_cents: 1234567, order_count: 88 },
      ingestion_run_id: 1,
      generated_at: '2026-08-19T12:00:00Z',
    },
  ],
  dashboard_action: {
    start_date: '2026-06-01',
    end_date: '2026-06-30',
    store_id: null,
    highlight_product: '牛肉poke',
  },
  suggestions: ['五月呢？', '按门店拆分'],
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(api.ask).mockResolvedValue(response);
});

test('answers with inspectable evidence and applies the linked dashboard action', async () => {
  const user = userEvent.setup();
  const onApply = vi.fn();
  render(<AiAssistant onApplyDashboardAction={onApply} />);

  await user.type(screen.getByLabelText('向 AI 提问'), '牛肉poke 六月卖了多少钱？');
  await user.click(screen.getByRole('button', { name: '发送问题' }));

  expect(await screen.findByText('牛肉poke 6月净营业额为 ¥12,345.67。')).toBeVisible();
  expect(screen.getByText('1 条可核验证据')).toBeVisible();
  await user.click(screen.getByText('1 条可核验证据'));
  expect(screen.getByText('get_revenue')).toBeVisible();
  expect(screen.getByText('¥12,345.67')).toBeVisible();

  await user.click(screen.getByRole('button', { name: '应用到看板' }));
  expect(onApply).toHaveBeenCalledWith(response.dashboard_action);
  expect(api.ask).toHaveBeenCalledWith('牛肉poke 六月卖了多少钱？', [], expect.any(AbortSignal));
});

test('keeps the typed question and offers retry after a request error', async () => {
  const user = userEvent.setup();
  vi.mocked(api.ask).mockRejectedValueOnce(new Error('network'));
  render(<AiAssistant onApplyDashboardAction={vi.fn()} />);

  await user.type(screen.getByLabelText('向 AI 提问'), '哪家门店表现最好？');
  await user.click(screen.getByRole('button', { name: '发送问题' }));

  expect(await screen.findByRole('alert')).toHaveTextContent('暂时无法完成分析');
  await user.click(screen.getByRole('button', { name: '重试' }));
  await waitFor(() => expect(api.ask).toHaveBeenCalledTimes(2));
});
