import { CalendarDays, SlidersHorizontal } from 'lucide-react';

import type { MetaResponse } from '../../api/types';
import type { DashboardFilterState } from './useDashboard';

interface FilterBarProps {
  meta: MetaResponse;
  value: DashboardFilterState;
  onChange: (value: DashboardFilterState) => void;
  onApply: (value?: DashboardFilterState) => void;
  refreshing: boolean;
}

export function FilterBar({ meta, value, onChange, onApply, refreshing }: FilterBarProps) {
  return (
    <section className="filter-panel" aria-label="看板筛选器">
      <div className="preset-row" aria-label="日期快捷选项">
        {meta.presets.map((preset) => {
          const active = value.startDate === preset.start_date && value.endDate === preset.end_date;
          return (
            <button
              className={`preset-chip ${active ? 'is-active' : ''}`}
              key={preset.label}
              type="button"
              onClick={() => {
                const next = { ...value, startDate: preset.start_date, endDate: preset.end_date };
                onChange(next);
                onApply(next);
              }}
            >
              {preset.label}
            </button>
          );
        })}
      </div>

      <form
        className="filter-form"
        onSubmit={(event) => {
          event.preventDefault();
          onApply();
        }}
      >
        <label className="field-group">
          <span>开始日期</span>
          <span className="input-wrap">
            <CalendarDays size={16} aria-hidden="true" />
            <input
              type="date"
              min={meta.date_range.min ?? undefined}
              max={meta.date_range.max ?? undefined}
              value={value.startDate}
              onChange={(event) => onChange({ ...value, startDate: event.target.value })}
            />
          </span>
        </label>
        <label className="field-group">
          <span>结束日期</span>
          <span className="input-wrap">
            <CalendarDays size={16} aria-hidden="true" />
            <input
              type="date"
              min={meta.date_range.min ?? undefined}
              max={meta.date_range.max ?? undefined}
              value={value.endDate}
              onChange={(event) => onChange({ ...value, endDate: event.target.value })}
            />
          </span>
        </label>
        <label className="field-group">
          <span>门店</span>
          <span className="input-wrap">
            <SlidersHorizontal size={16} aria-hidden="true" />
            <select
              aria-label="选择门店"
              value={value.storeId}
              onChange={(event) => onChange({ ...value, storeId: event.target.value })}
            >
              <option value="">全部门店</option>
              {meta.stores.map((store) => (
                <option value={store.store_id} key={store.store_id}>
                  {store.store_name} · {store.district}
                </option>
              ))}
            </select>
          </span>
        </label>
        <button className="primary-button" type="submit" disabled={refreshing}>
          {refreshing ? '更新中…' : '应用筛选'}
        </button>
      </form>
    </section>
  );
}

