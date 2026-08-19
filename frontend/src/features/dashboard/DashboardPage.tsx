import { useState } from 'react';
import { BadgeCheck, CircleDollarSign, ReceiptText, Sparkles, UsersRound } from 'lucide-react';

import { formatMoney, formatNumber } from '../../lib/format';
import { AiAssistant } from '../chat/AiAssistant';
import { DataQualityDrawer } from './DataQualityDrawer';
import { FilterBar } from './FilterBar';
import { KpiCard } from './KpiCard';
import { RevenueChart } from './RevenueChart';
import { StoreComparison } from './StoreComparison';
import { TopProducts } from './TopProducts';
import { useDashboard } from './useDashboard';

function LoadingDashboard() {
  return <div className="dashboard-skeleton" aria-label="正在加载经营数据"><div /><div /><div /><div /></div>;
}

export function DashboardPage() {
  const [qualityOpen, setQualityOpen] = useState(false);
  const {
    metaQuery,
    dashboardQuery,
    qualityQuery,
    qualityScore,
    draftFilters,
    setDraftFilters,
    applyFilters,
    applyDashboardAction,
    highlightedProduct,
  } = useDashboard();

  if (metaQuery.isLoading || !metaQuery.data) return <LoadingDashboard />;
  if (metaQuery.isError) {
    return <div className="fatal-state"><h1>暂时无法连接数据</h1><p>请确认后端服务已启动。</p><button onClick={() => metaQuery.refetch()}>重新连接</button></div>;
  }

  const dashboard = dashboardQuery.data;
  return (
    <main className="app-shell">
      <header className="app-header">
        <div className="brand-lockup">
          <div className="brand-mark"><span>店</span><Sparkles size={15} /></div>
          <div><p className="eyebrow">MONEKI OPERATIONS</p><h1>店务罗盘</h1><p>把每一笔经营数据，变成下一步行动。</p></div>
        </div>
        <button
          type="button"
          className="quality-button"
          onClick={() => setQualityOpen(true)}
          disabled={!qualityQuery.data}
          aria-label={`数据质量 ${qualityScore ?? '--'}%`}
        >
          <span className="quality-dot" />
          <span><small>数据质量</small><strong>{qualityScore ?? '--'}%</strong></span>
          <BadgeCheck size={19} />
        </button>
      </header>

      <FilterBar
        meta={metaQuery.data}
        value={draftFilters}
        onChange={setDraftFilters}
        onApply={applyFilters}
        refreshing={dashboardQuery.isFetching}
      />

      {dashboardQuery.isLoading && <LoadingDashboard />}
      {dashboardQuery.isError && (
        <div className="inline-error"><div><strong>这组筛选没有加载成功</strong><p>{dashboardQuery.error.message}</p></div><button onClick={() => dashboardQuery.refetch()}>重试</button></div>
      )}
      {dashboard && (
        <>
          <section className="overview-heading">
            <div><p className="section-kicker">EXECUTIVE SNAPSHOT</p><h2>经营概览</h2></div>
            <p>{dashboard.filters.start_date} — {dashboard.filters.end_date} · {dashboard.filters.store_id ?? '全部门店'} · {formatNumber(dashboard.coverage.valid_rows)} 条有效记录</p>
          </section>
          <section className="kpi-grid" aria-label="核心经营指标">
            <KpiCard label="净营业额" value={formatMoney(dashboard.summary.revenue)} change={dashboard.summary.revenue_change_percent} helper="较上一周期" icon={CircleDollarSign} tone="coral" />
            <KpiCard label="成交订单" value={formatNumber(dashboard.summary.order_count)} change={dashboard.summary.order_change_percent} helper="唯一订单数" icon={ReceiptText} tone="green" />
            <KpiCard label="平均客单价" value={formatMoney(dashboard.summary.average_order_value)} change={dashboard.summary.average_order_value_change_percent} helper="较上一周期" icon={UsersRound} tone="sand" />
          </section>
          <section className="insight-grid">
            <RevenueChart points={dashboard.daily} />
            <AiAssistant onApplyDashboardAction={applyDashboardAction} />
          </section>
          <section className="analysis-grid">
            <TopProducts products={dashboard.top_products} highlightedProduct={highlightedProduct} />
            <StoreComparison stores={dashboard.store_comparison} />
          </section>
        </>
      )}

      {qualityQuery.data && (
        <DataQualityDrawer data={qualityQuery.data} open={qualityOpen} onClose={() => setQualityOpen(false)} />
      )}
    </main>
  );
}
