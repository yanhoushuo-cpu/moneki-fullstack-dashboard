import type { ChatMessage, ChatResponse, ChatStreamEvent } from './types';

export interface ChatStreamOptions {
  signal?: AbortSignal;
  onEvent: (event: ChatStreamEvent) => void;
}

export class StreamProtocolError extends Error {}

function parseFrame(frame: string): ChatStreamEvent {
  let eventName = '';
  const dataLines: string[] = [];
  for (const line of frame.split('\n')) {
    if (line.startsWith('event:')) eventName = line.slice(6).trim();
    if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart());
  }
  if (!eventName || dataLines.length === 0) {
    throw new StreamProtocolError('收到无法识别的流式事件');
  }

  const payload = JSON.parse(dataLines.join('\n')) as Record<string, unknown>;
  switch (eventName) {
    case 'start':
      return { type: 'start' };
    case 'status':
      return { type: 'status', message: String(payload.message ?? '') };
    case 'delta':
      return { type: 'delta', text: String(payload.text ?? '') };
    case 'result':
      return { type: 'result', response: payload.response as unknown as ChatResponse };
    case 'done':
      return { type: 'done' };
    case 'error':
      return { type: 'error', message: String(payload.message ?? '流式传输中断，请重试。') };
    default:
      throw new StreamProtocolError(`未知流式事件：${eventName}`);
  }
}

export async function streamChat(
  message: string,
  history: ChatMessage[],
  options: ChatStreamOptions,
): Promise<ChatResponse> {
  const response = await fetch('/api/v1/chat/stream', {
    method: 'POST',
    headers: {
      Accept: 'text/event-stream',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ message, history }),
    signal: options.signal,
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as { detail?: unknown };
    const detail = typeof payload.detail === 'string' ? payload.detail : '请求失败，请稍后重试';
    throw new StreamProtocolError(detail);
  }
  if (!response.body) throw new StreamProtocolError('浏览器无法读取流式响应');

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let result: ChatResponse | null = null;
  let completed = false;

  const consume = (frame: string) => {
    if (!frame.trim()) return;
    const event = parseFrame(frame);
    options.onEvent(event);
    if (event.type === 'result') result = event.response;
    if (event.type === 'done') completed = true;
    if (event.type === 'error') throw new StreamProtocolError(event.message);
  };

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    buffer = buffer.replaceAll('\r\n', '\n');
    let boundary = buffer.indexOf('\n\n');
    while (boundary >= 0) {
      consume(buffer.slice(0, boundary));
      buffer = buffer.slice(boundary + 2);
      boundary = buffer.indexOf('\n\n');
    }
  }

  buffer += decoder.decode();
  buffer = buffer.replaceAll('\r\n', '\n');
  if (buffer.trim()) consume(buffer);
  if (!result || !completed) throw new StreamProtocolError('流式响应未正常完成');
  return result;
}
