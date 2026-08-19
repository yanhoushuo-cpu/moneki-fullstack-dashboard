import { CheckCircle2, CopyCheck, Database, ShieldCheck, WandSparkles, X } from 'lucide-react';

import type { DataQualityResponse } from '../../api/types';
import { formatNumber } from '../../lib/format';

interface DataQualityDrawerProps {
  data: DataQualityResponse;
  open: boolean;
  onClose: () => void;
}

export function DataQualityDrawer({ data, open, onClose }: DataQualityDrawerProps) {
  if (!open) return null;
  const summary = data.summary;
  return (
    <div className="drawer-layer">
      <button className="drawer-scrim" type="button" onClick={onClose} aria-label="关闭数据质量说明" />
      <aside className="quality-drawer" role="dialog" aria-modal="false" aria-label="数据质量说明">
        <header>
          <div className="drawer-icon"><ShieldCheck size={22} /></div>
          <div><p className="section-kicker">TRUST LEDGER</p><h2>数据质量说明</h2></div>
          <button className="icon-button" type="button" onClick={onClose} aria-label="关闭"><X size={20} /></button>
        </header>
        <p className="drawer-intro">每一条清洗规则都留下原因与行号，业务指标只使用通过校验的数据。</p>
        <div className="quality-stats">
          <div><Database size={18} /><span>原始记录</span><strong>{formatNumber(summary.raw_sales ?? 0)}</strong></div>
          <div><CheckCircle2 size={18} /><span>有效记录</span><strong>{formatNumber(summary.valid_sales ?? 0)}</strong></div>
          <div aria-label={`安全修复：${summary.amounts_imputed ?? 0}`}><WandSparkles size={18} /><span>安全修复</span><strong>{formatNumber(summary.amounts_imputed ?? 0)}</strong></div>
          <div aria-label={`移除重复：${summary.duplicate_rows_removed ?? 0}`}><CopyCheck size={18} /><span>移除重复</span><strong>{formatNumber(summary.duplicate_rows_removed ?? 0)}</strong></div>
          <div><ShieldCheck size={18} /><span>隔离记录</span><strong>{formatNumber(summary.quarantined_sales ?? 0)}</strong></div>
        </div>
        <h3>处理规则</h3>
        <ol className="quality-rules">
          {data.rules.map((rule) => (
            <li key={rule.code}><CheckCircle2 size={17} /><div><strong>{rule.label}</strong><p>{rule.action}</p></div></li>
          ))}
        </ol>
        <div className="quality-footnote">规则版本 {data.rule_version} · 数据批次 #{data.ingestion_run_id}</div>
      </aside>
    </div>
  );
}
