import type { Money } from '../api/types';

export function formatMoney(value: Money | null): string {
  return value?.formatted ?? '暂无数据';
}

export function formatCompactMoney(cents: number): string {
  const yuan = cents / 100;
  if (Math.abs(yuan) >= 10_000) {
    return `¥${(yuan / 10_000).toFixed(2)}万`;
  }
  return new Intl.NumberFormat('zh-CN', {
    style: 'currency',
    currency: 'CNY',
    minimumFractionDigits: 2,
  }).format(yuan);
}

export function formatPercent(value: number | null): string {
  if (value === null) return '暂无对比';
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(1)}%`;
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat('zh-CN').format(value);
}

export function formatDate(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', {
    month: 'short',
    day: 'numeric',
  }).format(new Date(`${value}T00:00:00`));
}

