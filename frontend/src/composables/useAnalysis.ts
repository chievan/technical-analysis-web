import { ref } from "vue";
import type { AnalysisRecord, AnalysisReport } from "../types";

export function useAnalysis() {
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function startAnalysis(symbol: string, model: string): Promise<string> {
    loading.value = true;
    error.value = null;

    const params = new URLSearchParams({ symbol, model });
    return `/api/v1/analysis/start?symbol=${encodeURIComponent(symbol)}&model=${encodeURIComponent(model)}`;
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

  return {
    loading,
    error,
    startAnalysis,
    fetchAnalysis,
    fetchReport,
    fetchHistory,
  };
}
