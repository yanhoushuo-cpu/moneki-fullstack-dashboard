import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, vi } from 'vitest';

import { api } from '../../api/client';
import type { DashboardResponse, DataQualityResponse, MetaResponse } from '../../api/types';
import { DashboardPage } from './DashboardPage';

vi.mock('../../api/client', () => ({
  api: {
    getMeta: vi.fn(),
    getDashboard: vi.fn(),
    getDataQuality: vi.fn(),
  },
}));

const meta: MetaResponse = {
  date_range: { min: '2026-05-01', max: '2026-07-31' },
  ingestion_run_id: 1,
  stores: [
    { store_id: 'S01', store_name: 'Makai Poke', category: '轻食', district: '上海·静安' },
  ],
  presets: [
    { label: '全部数据', start_date: '2026-05-01', end_date: '2026-07-31' },
    { label: '六月', start_date: '2026-06-01', end_date: '2026-06-30' },
  ],
};

const dashboard: DashboardResponse = {
  filters: { start_date: '2026-05-01', end_date: '2026-07-31', store_id: null },
  summary: {
    revenue: { cents: 4000, formatted: '¥40.00' },
    order_count: 2,
    average_order_value: { cents: 2000, formatted: '¥20.00' },
    previous_revenue: { cents: 3000, formatted: '¥30.00' },
    previous_order_count: 2,
    previous_average_order_value: { cents: 1500, formatted: '¥15.00' },
    revenue_change_percent: 33.3,
    order_change_percent: 0,
    average_order_value_change_percent: 33.3,
  },
  daily: [
    { date: '2026-05-01', revenue: { cents: 3000, formatted: '¥30.00' }, order_count: 1, average_order_value: { cents: 3000, formatted: '¥30.00' } },
    { date: '2026-05-02', revenue: { cents: 1000, formatted: '¥10.00' }, order_count: 1, average_order_value: { cents: 1000, formatted: '¥10.00' } },
  ],
  top_products: [
    { product_id: 'P01', product_name: '牛肉poke', product_category: '主食', quantity: 4, revenue: { cents: 4000, formatted: '¥40.00' }, order_count: 2 },
  ],
  store_comparison: [
    { store_id: 'S01', store_name: 'Makai Poke', category: '轻食', district: '上海·静安', revenue: { cents: 4000, formatted: '¥40.00' }, order_count: 2, share_percent: 100 },
  ],
  coverage: { valid_rows: 3, date_min: '2026-05-01', date_max: '2026-05-02', ingestion_run_id: 1, updated_at: '2026-08-19 10:01:00' },
};

const quality: DataQualityResponse = {
  ingestion_run_id: 1,
  source_hash: 'b'.repeat(64),
  rule_version: 'test',
  updated_at: '2026-08-19 10:01:00',
  summary: { raw_sales: 4, valid_sales: 3, duplicate_rows_removed: 1, amounts_imputed: 1, quarantined_sales: 0, issue_counts: {} },
  rules: [{ code: 'duplicate_row', label: '完全重复记录', action: '保留首次出现的记录' }],
};

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <DashboardPage />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.mocked(api.getMeta).mockResolvedValue(meta);
  vi.mocked(api.getDashboard).mockResolvedValue(dashboard);
  vi.mocked(api.getDataQuality).mockResolvedValue(quality);
});

test('renders trusted metrics and refetches when a store filter is applied', async () => {
  const user = userEvent.setup();
  renderPage();

  expect(await screen.findByLabelText('净营业额：¥40.00')).toBeVisible();
  expect(screen.getByText('牛肉poke')).toBeVisible();
  expect(screen.getByRole('button', { name: /数据质量/ })).toHaveTextContent('100%');

  await user.selectOptions(screen.getByLabelText('选择门店'), 'S01');
  await user.click(screen.getByRole('button', { name: '应用筛选' }));

  await waitFor(() =>
    expect(api.getDashboard).toHaveBeenLastCalledWith(
      { startDate: '2026-05-01', endDate: '2026-07-31', storeId: 'S01' },
      expect.any(AbortSignal),
    ),
  );
});

test('opens the data quality explanation without hiding the dashboard', async () => {
  const user = userEvent.setup();
  renderPage();
  await screen.findByLabelText('净营业额：¥40.00');

  await user.click(screen.getByRole('button', { name: /数据质量/ }));

  expect(screen.getByRole('dialog', { name: '数据质量说明' })).toBeVisible();
  expect(screen.getByText('完全重复记录')).toBeVisible();
  expect(screen.getByLabelText('安全修复：1')).toBeVisible();
  expect(screen.getByLabelText('移除重复：1')).toBeVisible();
  expect(screen.getByLabelText('净营业额：¥40.00')).toBeVisible();
});

test('shows a reconnect action instead of a permanent skeleton when metadata fails', async () => {
  const user = userEvent.setup();
  vi.mocked(api.getMeta).mockRejectedValueOnce(new Error('offline'));
  renderPage();

  expect(await screen.findByRole('heading', { name: '暂时无法连接数据' })).toBeVisible();
  expect(screen.queryByLabelText('正在加载经营数据')).not.toBeInTheDocument();

  await user.click(screen.getByRole('button', { name: '重新连接' }));
  expect(await screen.findByLabelText('净营业额：¥40.00')).toBeVisible();
});

test('surfaces a data quality request error and lets the user retry it', async () => {
  const user = userEvent.setup();
  vi.mocked(api.getDataQuality).mockRejectedValueOnce(new Error('quality offline'));
  renderPage();

  expect(await screen.findByLabelText('净营业额：¥40.00')).toBeVisible();
  expect(screen.getByRole('alert')).toHaveTextContent('数据质量信息暂时不可用');

  await user.click(screen.getByRole('button', { name: '重试数据质量' }));
  expect(await screen.findByRole('button', { name: '数据质量 100%' })).toBeEnabled();
  expect(screen.queryByText('数据质量信息暂时不可用')).not.toBeInTheDocument();
});
