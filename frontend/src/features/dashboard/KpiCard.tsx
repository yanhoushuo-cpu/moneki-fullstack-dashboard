import type { LucideIcon } from 'lucide-react';
import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react';

import { formatPercent } from '../../lib/format';

interface KpiCardProps {
  label: string;
  value: string;
  change: number | null;
  helper: string;
  icon: LucideIcon;
  tone?: 'coral' | 'green' | 'sand';
}

export function KpiCard({ label, value, change, helper, icon: Icon, tone = 'coral' }: KpiCardProps) {
  const DirectionIcon = change === null || change === 0 ? Minus : change > 0 ? ArrowUpRight : ArrowDownRight;
  const direction = change === null ? 'neutral' : change > 0 ? 'positive' : change < 0 ? 'negative' : 'neutral';
  return (
    <article className={`kpi-card tone-${tone}`} aria-label={`${label}：${value}`}>
      <div className="kpi-heading">
        <span>{label}</span>
        <span className="kpi-icon"><Icon size={18} aria-hidden="true" /></span>
      </div>
      <strong>{value}</strong>
      <div className={`kpi-change ${direction}`}>
        <DirectionIcon size={15} aria-hidden="true" />
        <span>{formatPercent(change)}</span>
        <small>{helper}</small>
      </div>
    </article>
  );
}

