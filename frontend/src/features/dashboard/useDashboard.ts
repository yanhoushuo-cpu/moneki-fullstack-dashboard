import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';

import { api } from '../../api/client';
import type { DashboardAction } from '../../api/types';

export interface DashboardFilterState {
  startDate: string;
  endDate: string;
  storeId: string;
}

const EMPTY_FILTERS: DashboardFilterState = { startDate: '', endDate: '', storeId: '' };

export function useDashboard() {
  const metaQuery = useQuery({
    queryKey: ['meta'],
    queryFn: ({ signal }) => api.getMeta(signal),
  });
  const [draftFilters, setDraftFilters] = useState(EMPTY_FILTERS);
  const [filters, setFilters] = useState<DashboardFilterState | null>(null);
  const [highlightedProduct, setHighlightedProduct] = useState<string | null>(null);

  useEffect(() => {
    const range = metaQuery.data?.date_range;
    if (!filters && range?.min && range.max) {
      const initial = { startDate: range.min, endDate: range.max, storeId: '' };
      setDraftFilters(initial);
      setFilters(initial);
    }
  }, [filters, metaQuery.data]);

  const dashboardQuery = useQuery({
    queryKey: ['dashboard', filters],
    queryFn: ({ signal }) =>
      api.getDashboard(
        {
          startDate: filters!.startDate,
          endDate: filters!.endDate,
          storeId: filters!.storeId || null,
        },
        signal,
      ),
    enabled: filters !== null,
    placeholderData: (previous) => previous,
  });

  const qualityQuery = useQuery({
    queryKey: ['data-quality'],
    queryFn: ({ signal }) => api.getDataQuality(signal),
  });

  const qualityScore = useMemo(() => {
    const summary = qualityQuery.data?.summary;
    if (!summary?.raw_sales || summary.valid_sales === undefined) return null;
    const comparableRows = summary.raw_sales - (summary.duplicate_rows_removed ?? 0);
    if (comparableRows <= 0) return null;
    return Math.round((summary.valid_sales / comparableRows) * 100);
  }, [qualityQuery.data]);

  function applyFilters(next = draftFilters) {
    if (!next.startDate || !next.endDate) return;
    setFilters(next);
    setHighlightedProduct(null);
  }

  function applyDashboardAction(action: DashboardAction) {
    const next = {
      startDate: action.start_date,
      endDate: action.end_date,
      storeId: action.store_id ?? '',
    };
    setDraftFilters(next);
    setFilters(next);
    setHighlightedProduct(action.highlight_product);
  }

  return {
    metaQuery,
    dashboardQuery,
    qualityQuery,
    qualityScore,
    draftFilters,
    setDraftFilters,
    applyFilters,
    applyDashboardAction,
    highlightedProduct,
  };
}
