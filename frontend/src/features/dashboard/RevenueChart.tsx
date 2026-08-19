import { useState } from 'react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import type { DailyPoint } from '../../api/types';
import { formatCompactMoney, formatDate, formatNumber } from '../../lib/format';

type Metric = 'revenue' | 'orders' | 'aov';

const METRICS: Array<{ value: Metric; label: string }> = [
  { value: 'revenue', label: '营业额' },
  { value: 'orders', label: '订单数' },
  { value: 'aov', label: '客单价' },
];

export function RevenueChart({ points }: { points: DailyPoint[] }) {
  const [metric, setMetric] = useState<Metric>('revenue');
  const chartData = points.map((point) => ({
    date: point.date,
    revenue: point.revenue.cents,
    orders: point.order_count,
    aov: point.average_order_value?.cents ?? 0,
  }));
  const formatter = metric === 'orders' ? (value: number) => formatNumber(value) : formatCompactMoney;

  return (
    <section className="panel chart-panel" aria-labelledby="trend-title">
      <header className="panel-heading">
        <div>
          <p className="section-kicker">PERFORMANCE PULSE</p>
          <h2 id="trend-title">经营趋势</h2>
          <p>按日观察波动，快速定位高峰与回落。</p>
        </div>
        <div className="segmented-control" aria-label="趋势指标">
          {METRICS.map((item) => (
            <button
              type="button"
              key={item.value}
              className={metric === item.value ? 'is-active' : ''}
              aria-pressed={metric === item.value}
              onClick={() => setMetric(item.value)}
            >
              {item.label}
            </button>
          ))}
        </div>
      </header>
      {chartData.length ? (
        <>
          <p className="sr-only">
            当前展示 {chartData.length} 天{METRICS.find((item) => item.value === metric)?.label}趋势。
          </p>
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 12, right: 10, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="revenue-fill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#e85d3f" stopOpacity={0.32} />
                    <stop offset="100%" stopColor="#e85d3f" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="#e8e0d4" strokeDasharray="4 5" vertical={false} />
                <XAxis dataKey="date" tickFormatter={formatDate} tickLine={false} axisLine={false} minTickGap={28} />
                <YAxis tickFormatter={formatter} tickLine={false} axisLine={false} width={68} />
                <Tooltip
                  labelFormatter={(value) => formatDate(String(value))}
                  formatter={(value) => [formatter(Number(value)), METRICS.find((item) => item.value === metric)?.label]}
                  contentStyle={{ borderRadius: 14, border: '1px solid #ddd5c8', boxShadow: '0 12px 30px rgb(82 63 40 / 12%)' }}
                />
                <Area type="monotone" dataKey={metric} stroke="#d84c31" strokeWidth={3} fill="url(#revenue-fill)" activeDot={{ r: 5, fill: '#fff', strokeWidth: 3 }} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </>
      ) : (
        <div className="empty-state">所选范围没有趋势数据，请调整筛选条件。</div>
      )}
    </section>
  );
}

