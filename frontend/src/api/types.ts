export interface Money {
  cents: number;
  formatted: string;
}

export interface DashboardFilters {
  start_date: string;
  end_date: string;
  store_id: string | null;
}

export interface DashboardSummary {
  revenue: Money;
  order_count: number;
  average_order_value: Money | null;
  previous_revenue: Money;
  previous_order_count: number;
  previous_average_order_value: Money | null;
  revenue_change_percent: number | null;
  order_change_percent: number | null;
  average_order_value_change_percent: number | null;
}

export interface DailyPoint {
  date: string;
  revenue: Money;
  order_count: number;
  average_order_value: Money | null;
}

export interface TopProduct {
  product_id: string;
  product_name: string;
  product_category: string;
  quantity: number;
  revenue: Money;
  order_count: number;
}

export interface StoreComparison {
  store_id: string;
  store_name: string;
  category: string;
  district: string;
  revenue: Money;
  order_count: number;
  share_percent: number;
}

export interface Coverage {
  valid_rows: number;
  date_min: string | null;
  date_max: string | null;
  ingestion_run_id: number;
  updated_at: string;
}

export interface DashboardResponse {
  filters: DashboardFilters;
  summary: DashboardSummary;
  daily: DailyPoint[];
  top_products: TopProduct[];
  store_comparison: StoreComparison[];
  coverage: Coverage;
}

export interface StoreOption {
  store_id: string;
  store_name: string;
  category: string;
  district: string;
}

export interface DatePreset {
  label: string;
  start_date: string;
  end_date: string;
}

export interface MetaResponse {
  date_range: { min: string | null; max: string | null };
  stores: StoreOption[];
  ingestion_run_id: number;
  presets: DatePreset[];
}

export interface QualityRule {
  code: string;
  label: string;
  action: string;
}

export interface DataQualityResponse {
  ingestion_run_id: number;
  source_hash: string;
  rule_version: string;
  updated_at: string;
  summary: {
    raw_sales?: number;
    duplicate_rows_removed?: number;
    amounts_imputed?: number;
    valid_sales?: number;
    quarantined_sales?: number;
    issue_counts?: Record<string, number>;
    date_min?: string;
    date_max?: string;
  };
  rules: QualityRule[];
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface Evidence {
  tool: string;
  parameters: Record<string, unknown>;
  result: Record<string, unknown>;
  ingestion_run_id: number;
  generated_at: string;
}

export interface DashboardAction {
  start_date: string;
  end_date: string;
  store_id: string | null;
  highlight_product: string | null;
}

export interface ChatResponse {
  answer: string;
  status: 'answered' | 'unsupported' | 'unavailable';
  mode: 'mock' | 'provider';
  evidence: Evidence[];
  dashboard_action: DashboardAction | null;
  suggestions: string[];
}

export type ChatStreamEvent =
  | { type: 'start' }
  | { type: 'status'; message: string }
  | { type: 'delta'; text: string }
  | { type: 'result'; response: ChatResponse }
  | { type: 'done' }
  | { type: 'error'; message: string };
