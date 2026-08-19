import { afterEach, expect, test, vi } from 'vitest';

import type { ChatResponse, ChatStreamEvent } from './types';
import { streamChat } from './chatStream';

const responsePayload: ChatResponse = {
  answer: '牛肉',
  status: 'answered',
  mode: 'mock',
  evidence: [],
  dashboard_action: null,
  suggestions: [],
};

function sse(event: string, data: object) {
  return `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
}

function byteSplitResponse(body: string) {
  const bytes = new TextEncoder().encode(body);
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      bytes.forEach((byte) => controller.enqueue(Uint8Array.of(byte)));
      controller.close();
    },
  });
  return new Response(stream, {
    status: 200,
    headers: { 'Content-Type': 'text/event-stream' },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

test('reassembles UTF-8 text and SSE frames split across arbitrary bytes', async () => {
  const body = [
    sse('start', {}),
    sse('status', { message: '正在查询' }),
    sse('delta', { text: '牛' }),
    sse('delta', { text: '肉' }),
    sse('result', { response: responsePayload }),
    sse('done', {}),
  ].join('');
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(byteSplitResponse(body)));
  const seen: ChatStreamEvent[] = [];

  const result = await streamChat('问题', [], { onEvent: (event) => seen.push(event) });

  expect(seen.filter((event) => event.type === 'delta')).toEqual([
    { type: 'delta', text: '牛' },
    { type: 'delta', text: '肉' },
  ]);
  expect(result).toEqual(responsePayload);
  expect(fetch).toHaveBeenCalledWith('/api/v1/chat/stream', expect.objectContaining({
    method: 'POST',
    headers: expect.objectContaining({ Accept: 'text/event-stream' }),
    body: JSON.stringify({ message: '问题', history: [] }),
  }));
});

test('surfaces an HTTP validation detail before reading a stream', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(
    JSON.stringify({ detail: '输入无效' }),
    { status: 422, headers: { 'Content-Type': 'application/json' } },
  )));

  await expect(streamChat('', [], { onEvent: vi.fn() })).rejects.toThrow('输入无效');
});

test('rejects a server error event', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(byteSplitResponse(
    sse('start', {}) + sse('error', { message: '流式传输中断，请重试。' }),
  )));

  await expect(streamChat('问题', [], { onEvent: vi.fn() })).rejects.toThrow('流式传输中断，请重试。');
});

test('rejects a stream that closes before result and done', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(byteSplitResponse(
    sse('start', {}) + sse('delta', { text: '未完成' }),
  )));

  await expect(streamChat('问题', [], { onEvent: vi.fn() })).rejects.toThrow('流式响应未正常完成');
});
