export type SSEEventType =
  | "thinking"
  | "tool_call"
  | "tool_result"
  | "report_chunk"
  | "chart_data"
  | "report_complete"
  | "error"
  | "done";

export interface SSEEvent {
  type: SSEEventType;
  content: string;
  analysis_id?: string;
  skill_version?: string;
}

export interface AnalysisRecord {
  id: string;
  symbol: string;
  symbol_name: string;
  model: string;
  skill_version: string;
  status: string;
  conclusion: string;
  created_at: string;
}

export interface AnalysisStep {
  id: number;
  analysis_id: string;
  step_type: string;
  content: string;
  extra: string;
  created_at: string;
}

export interface BacktestResult {
  id: string;
  symbol: string;
  skill_version: string;
  parameters: string;
  results: string;
  report_md: string;
  chart_data: string;
  created_at: string;
}

export interface AnalysisReport {
  id: string;
  analysis_id: string;
  report_md: string;
  report_html: string;
  chart_data: string;
  key_levels: string;
  five_dimension: string;
  created_at: string;
}

// Chart data structures for KLineChart
export interface KLineData {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface BBSeries {
  upper: number;
  middle: number;
  lower: number;
}

export interface MACDSeries {
  dif: number;
  dea: number;
  histogram: number;
}

export interface ChartData {
  symbol: string;
  symbol_name: string;
  klines: KLineData[];
  ma5_series: number[];
  ma10_series: number[];
  ma20_series: number[];
  ma60_series: number[];
  macd_series: MACDSeries[];
  rsi_series: number[];
  bollinger_series: BBSeries[];
  moving_averages: Record<string, unknown>;
  support_levels?: number[];
  resistance_levels?: number[];
  [key: string]: unknown;
}
