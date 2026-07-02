import { ref } from "vue";
import type { AnalysisRecord, AnalysisReport } from "../types";

export function useAnalysis() {
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function checkAnalysis(
    symbol: string,
    date?: string
  ): Promise<{
    report_exists: boolean;
    analysis_id?: string;
    conclusion?: string;
    created_at?: string;
  }> {
    const params = new URLSearchParams({ symbol });
    if (date) params.set("date", date);
    const res = await fetch(`/api/v1/analysis/check?${params}`);
    if (!res.ok) throw new Error("Failed to check analysis");
    return res.json();
  }

  async function startAnalysis(
    symbol: string,
    model: string,
    force?: boolean
  ): Promise<string> {
    loading.value = true;
    error.value = null;

    const params = new URLSearchParams({ symbol, model });
    if (force) params.set("force", "true");
    return `/api/v1/analysis/start?${params}`;
  }

  async function fetchAnalysis(id: string): Promise<AnalysisRecord> {
    const res = await fetch(`/api/v1/analysis/${id}`);
    if (!res.ok) throw new Error("Failed to fetch analysis");
    return res.json();
  }

  async function fetchReport(id: string): Promise<AnalysisReport> {
    const res = await fetch(`/api/v1/analysis/${id}/report`);
    if (!res.ok) throw new Error("Failed to fetch report");
    return res.json();
  }

  async function fetchChartData(id: string): Promise<string | null> {
    try {
      const report = await fetchReport(id);
      return report.chart_data && report.chart_data !== "{}"
        ? report.chart_data
        : null;
    } catch {
      return null;
    }
  }

  async function fetchHistory(params?: {
    symbol?: string;
    skill_version?: string;
    limit?: number;
    offset?: number;
  }): Promise<AnalysisRecord[]> {
    const q = new URLSearchParams();
    if (params?.symbol) q.set("symbol", params.symbol);
    if (params?.skill_version) q.set("skill_version", params.skill_version);
    if (params?.limit) q.set("limit", String(params.limit));
    if (params?.offset) q.set("offset", String(params.offset));

    const res = await fetch(`/api/v1/analysis/history?${q}`);
    if (!res.ok) throw new Error("Failed to fetch history");
    return res.json();
  }

  async function downloadReport(
    id: string,
    format: "md" | "html"
  ): Promise<void> {
    try {
      const report = await fetchReport(id);
      const content =
        format === "md"
          ? report.report_md
          : report.report_html || report.report_md;
      const ext = format === "md" ? "md" : "html";
      const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `analysis-${id.slice(0, 8)}.${ext}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // download failed silently
    }
  }

  return {
    loading,
    error,
    checkAnalysis,
    startAnalysis,
    fetchAnalysis,
    fetchReport,
    fetchChartData,
    fetchHistory,
    downloadReport,
  };
}
