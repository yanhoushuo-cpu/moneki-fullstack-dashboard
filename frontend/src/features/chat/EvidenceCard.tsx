import { Braces, CheckCircle2 } from 'lucide-react';

import type { Evidence } from '../../api/types';

const TOOL_LABELS: Record<string, string> = {
  get_revenue: '营业额查询',
  get_top_entities: '排行查询',
  compare_periods: '周期对比',
  get_trend: '趋势查询',
  get_data_quality: '质量审计',
};

function labelFor(key: string) {
  return key
    .replace(/_cents$/, '')
    .replaceAll('_', ' ')
    .replace(/^./, (value) => value.toUpperCase());
}

function displayValue(key: string, value: unknown) {
  if (key.endsWith('_cents') && typeof value === 'number') {
    return new Intl.NumberFormat('zh-CN', { style: 'currency', currency: 'CNY' }).format(value / 100);
  }
  if (value === null) return '—';
  if (typeof value === 'object') return JSON.stringify(value, null, 2);
  return String(value);
}

export function EvidenceCard({ evidence, index }: { evidence: Evidence; index: number }) {
  return (
    <article className="evidence-card">
      <header>
        <span><CheckCircle2 size={14} /> 证据 {index + 1}</span>
        <small>批次 #{evidence.ingestion_run_id}</small>
      </header>
      <div className="evidence-tool"><Braces size={15} /><div><strong>{TOOL_LABELS[evidence.tool] ?? evidence.tool}</strong><code>{evidence.tool}</code></div></div>
      <dl>
        {Object.entries(evidence.result).map(([key, value]) => (
          <div key={key}><dt>{labelFor(key)}</dt><dd>{displayValue(key, value)}</dd></div>
        ))}
      </dl>
      <details>
        <summary>查看查询参数</summary>
        <pre>{JSON.stringify(evidence.parameters, null, 2)}</pre>
      </details>
    </article>
  );
}
