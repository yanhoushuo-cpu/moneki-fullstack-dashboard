import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, expect, test, vi } from 'vitest';

import { api } from '../../api/client';
import type { ChatResponse } from '../../api/types';
import { AiAssistant } from './AiAssistant';

vi.mock('../../api/client', () => ({ api: { askStream: vi.fn() } }));

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
  vi.mocked(api.askStream).mockImplementation(async (_message, _history, options) => {
    options.onEvent({ type: 'status', message: '正在查询可信经营数据…' });
    options.onEvent({ type: 'delta', text: '牛肉poke 6月' });
    options.onEvent({ type: 'delta', text: '净营业额为 ¥12,345.67。' });
    options.onEvent({ type: 'result', response });
    options.onEvent({ type: 'done' });
    return response;
  });
});

test('only offers standalone supported questions before any conversation', () => {
  render(<AiAssistant onApplyDashboardAction={vi.fn()} />);

  expect(screen.queryByRole('button', { name: '五月呢？' })).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: '这批数据有哪些质量问题？' })).toBeVisible();
  expect(screen.getByLabelText('向 AI 提问')).toHaveAttribute(
    'placeholder',
    '例如：牛肉poke 六月卖了多少钱？',
  );
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
  expect(api.askStream).toHaveBeenCalledWith(
    '牛肉poke 六月卖了多少钱？',
    [],
    expect.objectContaining({ signal: expect.any(AbortSignal), onEvent: expect.any(Function) }),
  );
});

test('keeps the typed question and offers retry after a request error', async () => {
  const user = userEvent.setup();
  vi.mocked(api.askStream).mockRejectedValueOnce(new Error('network'));
  render(<AiAssistant onApplyDashboardAction={vi.fn()} />);

  await user.type(screen.getByLabelText('向 AI 提问'), '哪家门店表现最好？');
  await user.click(screen.getByRole('button', { name: '发送问题' }));

  expect(await screen.findByRole('alert')).toHaveTextContent('暂时无法完成分析');
  await user.click(screen.getByRole('button', { name: '重试' }));
  await waitFor(() => expect(api.askStream).toHaveBeenCalledTimes(2));
});

test('shows streamed text before the final response resolves', async () => {
  const user = userEvent.setup();
  let finish: ((value: ChatResponse) => void) | undefined;
  let emit: Parameters<typeof api.askStream>[2]['onEvent'] | undefined;
  vi.mocked(api.askStream).mockImplementation((_message, _history, options) => {
    emit = options.onEvent;
    options.onEvent({ type: 'status', message: '正在查询可信经营数据…' });
    options.onEvent({ type: 'delta', text: '先到达的部分回答' });
    return new Promise<ChatResponse>((resolve) => { finish = resolve; });
  });
  render(<AiAssistant onApplyDashboardAction={vi.fn()} />);

  await user.type(screen.getByLabelText('向 AI 提问'), '牛肉poke 六月卖了多少钱？');
  await user.click(screen.getByRole('button', { name: '发送问题' }));

  expect(await screen.findByText('先到达的部分回答')).toBeVisible();
  expect(screen.getByText('流式传输 · 数据库规则分析')).toBeVisible();
  expect(screen.queryByText('1 条可核验证据')).not.toBeInTheDocument();

  await act(async () => {
    emit?.({ type: 'result', response });
    emit?.({ type: 'done' });
    finish?.(response);
  });
  expect(await screen.findByText(response.answer)).toBeVisible();
  expect(screen.getByText('1 条可核验证据')).toBeVisible();
});

test('submitting a new question aborts the previous stream', async () => {
  const user = userEvent.setup();
  let firstSignal: AbortSignal | undefined;
  vi.mocked(api.askStream)
    .mockImplementationOnce((_message, _history, options) => {
      firstSignal = options.signal;
      return new Promise<ChatResponse>((_resolve, reject) => {
        options.signal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')));
      });
    })
    .mockImplementationOnce(async (_message, _history, options) => {
      options.onEvent({ type: 'delta', text: response.answer });
      options.onEvent({ type: 'result', response });
      options.onEvent({ type: 'done' });
      return response;
    });
  render(<AiAssistant onApplyDashboardAction={vi.fn()} />);

  await user.type(screen.getByLabelText('向 AI 提问'), '第一个问题');
  await user.click(screen.getByRole('button', { name: '发送问题' }));
  await user.type(screen.getByLabelText('向 AI 提问'), '第二个问题');
  await user.click(screen.getByRole('button', { name: '发送问题' }));

  await waitFor(() => expect(api.askStream).toHaveBeenCalledTimes(2));
  expect(firstSignal?.aborted).toBe(true);
});

test('stops an active stream without presenting it as a network failure', async () => {
  const user = userEvent.setup();
  let activeSignal: AbortSignal | undefined;
  vi.mocked(api.askStream).mockImplementationOnce((_message, _history, options) => {
    activeSignal = options.signal;
    return new Promise<ChatResponse>((_resolve, reject) => {
      options.signal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')));
    });
  });
  render(<AiAssistant onApplyDashboardAction={vi.fn()} />);

  await user.type(screen.getByLabelText('向 AI 提问'), '停止这个问题');
  await user.click(screen.getByRole('button', { name: '发送问题' }));
  await user.click(await screen.findByRole('button', { name: '停止生成' }));

  await waitFor(() => expect(activeSignal?.aborted).toBe(true));
  expect(screen.getByLabelText('向 AI 提问')).toHaveValue('停止这个问题');
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});
