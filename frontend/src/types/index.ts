export type SSEEventType =
  "thinking" | "tool_call" | "tool_result" | "report_chunk" | "error" | "done";

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
  metadata: string;
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
