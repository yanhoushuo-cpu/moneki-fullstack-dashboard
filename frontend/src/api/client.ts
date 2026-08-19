import type {
  ChatMessage,
  ChatResponse,
  DashboardResponse,
  DataQualityResponse,
  MetaResponse,
} from './types';

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => ({}))) as { detail?: string };
    throw new ApiError(payload.detail ?? '请求失败，请稍后重试', response.status);
  }
  return (await response.json()) as T;
}

export const api = {
  getMeta: (signal?: AbortSignal) => request<MetaResponse>('/meta', { signal }),
  getDashboard: (
    filters: { startDate: string; endDate: string; storeId?: string | null },
    signal?: AbortSignal,
  ) => {
    const params = new URLSearchParams({
      start_date: filters.startDate,
      end_date: filters.endDate,
    });
    if (filters.storeId) params.set('store_id', filters.storeId);
    return request<DashboardResponse>(`/dashboard?${params}`, { signal });
  },
  getDataQuality: (signal?: AbortSignal) =>
    request<DataQualityResponse>('/data-quality', { signal }),
  ask: (message: string, history: ChatMessage[], signal?: AbortSignal) =>
    request<ChatResponse>('/chat', {
      method: 'POST',
      body: JSON.stringify({ message, history: history.slice(-8) }),
      signal,
    }),
};

