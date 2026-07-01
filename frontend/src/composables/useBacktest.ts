import { ref } from "vue";
import type { BacktestResult } from "../types";

export function useBacktest() {
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function startBacktest(params: {
    symbol: string;
    start_date?: string;
    end_date?: string;
    initial_capital?: number;
    strategy?: string;
    ma_short?: number;
    ma_long?: number;
  }): Promise<BacktestResult> {
    loading.value = true;
    error.value = null;
    const q = new URLSearchParams({ symbol: params.symbol });
    if (params.start_date) q.set("start_date", params.start_date);
    if (params.end_date) q.set("end_date", params.end_date);
    if (params.initial_capital)
      q.set("initial_capital", String(params.initial_capital));
    if (params.strategy) q.set("strategy", params.strategy);
    if (params.ma_short) q.set("ma_short", String(params.ma_short));
    if (params.ma_long) q.set("ma_long", String(params.ma_long));
    const res = await fetch(`/api/v1/backtest/start?${q}`, { method: "POST" });
    if (!res.ok) {
      const err = await res.text();
      throw new Error(err);
    }
    return res.json();
  }

  async function fetchBacktestHistory(params?: {
    symbol?: string;
    date_from?: string;
    date_to?: string;
    limit?: number;
    offset?: number;
  }): Promise<BacktestResult[]> {
    const q = new URLSearchParams();
    if (params?.symbol) q.set("symbol", params.symbol);
    if (params?.date_from) q.set("date_from", params.date_from);
    if (params?.date_to) q.set("date_to", params.date_to);
    if (params?.limit) q.set("limit", String(params.limit));
    if (params?.offset) q.set("offset", String(params.offset));
    const res = await fetch(`/api/v1/backtest/history?${q}`);
    if (!res.ok) throw new Error("Failed to fetch backtest history");
    return res.json();
  }

  async function fetchBacktest(id: string): Promise<BacktestResult> {
    const res = await fetch(`/api/v1/backtest/${id}`);
    if (!res.ok) throw new Error("Failed to fetch backtest");
    return res.json();
  }

  function downloadBacktestReport(result: BacktestResult): void {
    const content =
      result.report_md ||
      JSON.stringify(
        {
          symbol: result.symbol,
          total_return_pct: result.total_return_pct,
          max_drawdown_pct: result.max_drawdown_pct,
          win_rate: result.win_rate,
          total_trades: result.total_trades,
        },
        null,
        2
      );
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `backtest-${result.symbol}-${result.id.slice(0, 8)}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return {
    loading,
    error,
    startBacktest,
    fetchBacktestHistory,
    fetchBacktest,
    downloadBacktestReport,
  };
}
