<script setup lang="ts">
import { ref, watch, onMounted } from "vue";
import { useRouter } from "vue-router";
import WatchlistSidebar from "../components/WatchlistSidebar.vue";
import type { WatchlistItem } from "../components/WatchlistSidebar.vue";
import AnalysisModal from "../components/AnalysisModal.vue";
import ReportViewer from "../components/ReportViewer.vue";
import KLineChart from "../components/KLineChart.vue";
import BacktestForm from "../components/BacktestForm.vue";
import BacktestReport from "../components/BacktestReport.vue";
import type { ChartData } from "../types";
import { useSSE } from "../composables/useSSE";
import { useAnalysis } from "../composables/useAnalysis";
import type { AnalysisRecord, AnalysisReport, BacktestResult } from "../types";

const router = useRouter();

/* ─── Watchlist ─── */
const STORAGE_KEY = "ta-watchlist";
const defaultWatchlist: WatchlistItem[] = [
  { code: "000300", name: "沪深300" },
  { code: "600519", name: "贵州茅台" },
  { code: "600909", name: "华安证券" },
  { code: "TL", name: "30年期国债期货" },
];

function loadWatchlist(): WatchlistItem[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw) as WatchlistItem[];
  } catch {
    /* ignore */
  }
  return defaultWatchlist;
}

function saveWatchlist() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(watchlist.value));
}

const watchlist = ref<WatchlistItem[]>(loadWatchlist());
const selectedStock = ref(""); // resolved on mount

/* ─── On mount: pick the most recently analyzed stock ─── */
onMounted(async () => {
  try {
    const recent = await fetchHistory({ limit: 1 });
    if (recent.length > 0 && recent[0].status === "completed") {
      const sym = recent[0].symbol;
      // Ensure it's in the watchlist
      if (!watchlist.value.some((s) => s.code === sym)) {
        watchlist.value.unshift({
          code: sym,
          name: recent[0].symbol_name || sym,
        });
        saveWatchlist();
      }
      selectedStock.value = sym;
      return;
    }
  } catch {
    /* network error, fall through */
  }
  // No recent analysis → fall back to first watchlist item
  selectedStock.value = watchlist.value[0]?.code || "000300";
});

function onSelectStock(code: string) {
  selectedStock.value = code;
}
function onAddStock(code: string) {
  const name = code; // will be refined by backend response
  if (!watchlist.value.some((s) => s.code === code)) {
    watchlist.value.push({ code, name });
    saveWatchlist();
  }
}
function onRemoveStock(code: string) {
  watchlist.value = watchlist.value.filter((s) => s.code !== code);
  if (selectedStock.value === code) {
    selectedStock.value = watchlist.value[0]?.code || "";
  }
  saveWatchlist();
}

/* ─── State ─── */
const model = ref("deepseek-chat");
const analyzing = ref(false);
const showAnalysisModal = ref(false);
const showOverwriteConfirm = ref(false);
const pendingAnalysisDate = ref("");
const existingAnalysisId = ref<string | null>(null);
const finalReport = ref<AnalysisReport | null>(null);
const chartData = ref<ChartData | null>(null);
const sameSymbolHistory = ref<AnalysisRecord[]>([]);
const showHistory = ref(false);
const showBacktestForm = ref(false);
const backtestResult = ref<BacktestResult | null>(null);

/* ─── Composables ─── */
const { events, done, error, analysisId, chartDataStr, connect, disconnect } =
  useSSE();
const {
  fetchReport,
  fetchHistory,
  fetchChartData,
  downloadReport,
  checkAnalysis,
} = useAnalysis();

/* ─── SSE event handlers ─── */
watch(chartDataStr, (val) => {
  if (val) {
    try {
      chartData.value = JSON.parse(val) as ChartData;
    } catch {
      chartData.value = null;
    }
  }
});

watch(done, async (val) => {
  if (val && analysisId.value) {
    analyzing.value = false;
    try {
      finalReport.value = await fetchReport(analysisId.value);
      if (!chartData.value) {
        const saved = await fetchChartData(analysisId.value);
        if (saved) {
          try {
            chartData.value = JSON.parse(saved) as ChartData;
          } catch {
            /* ignore */
          }
        }
      }
    } catch {
      error.value = "分析报告加载失败，请尝试重新分析";
    }
  }
});

watch(finalReport, async (report) => {
  if (report) {
    try {
      const records = await fetchHistory({
        symbol: selectedStock.value,
        limit: 5,
      });
      sameSymbolHistory.value = records.filter(
        (r) => r.id !== analysisId.value
      );
      showHistory.value = sameSymbolHistory.value.length > 0;
    } catch {
      sameSymbolHistory.value = [];
    }
  }
});

/* ─── Actions ─── */
async function startAnalysis() {
  if (!selectedStock.value.trim()) return;
  finalReport.value = null;
  chartData.value = null;
  sameSymbolHistory.value = [];
  showHistory.value = false;

  // Check for existing report first
  try {
    const check = await checkAnalysis(selectedStock.value);
    if (check.report_exists) {
      pendingAnalysisDate.value = new Date().toISOString().slice(0, 10);
      existingAnalysisId.value = check.analysis_id || null;
      showOverwriteConfirm.value = true;
      return;
    }
  } catch {
    // Network error — proceed directly
  }

  doStartAnalysis(false);
}

function doStartAnalysis(force: boolean) {
  analyzing.value = true;
  showAnalysisModal.value = true;

  const url = `/api/v1/analysis/start?symbol=${encodeURIComponent(selectedStock.value)}&model=${encodeURIComponent(model.value)}${force ? "&force=true" : ""}`;
  connect(url);
}

function confirmOverwrite() {
  showOverwriteConfirm.value = false;
  doStartAnalysis(true);
}

function cancelOverwrite() {
  showOverwriteConfirm.value = false;
  // Load existing report
  if (existingAnalysisId.value) {
    fetchReport(existingAnalysisId.value)
      .then((r) => {
        finalReport.value = r;
        fetchChartData(existingAnalysisId.value!)
          .then((saved) => {
            if (saved) {
              try {
                chartData.value = JSON.parse(saved) as ChartData;
              } catch {
                chartData.value = null;
              }
            }
          })
          .catch(() => {});
      })
      .catch(() => {});
  }
}

function closeAnalysis() {
  showAnalysisModal.value = false;
  if (!done.value) {
    disconnect();
    analyzing.value = false;
  }
}

function goHistory() {
  router.push("/history");
}

function goBacktestHistory() {
  router.push("/backtest");
}

function goVersions() {
  router.push("/versions");
}

/* ─── Try to load existing report on stock select ─── */
watch(selectedStock, async (symbol) => {
  if (!symbol) return;
  try {
    const records = await fetchHistory({ symbol, limit: 1 });
    if (records.length > 0) {
      const rec = records[0];
      // Update stock name if available
      if (rec.symbol_name) {
        const item = watchlist.value.find((s) => s.code === symbol);
        if (item && item.name !== rec.symbol_name) {
          item.name = rec.symbol_name;
          saveWatchlist();
        }
      }
      finalReport.value = await fetchReport(rec.id).catch(() => null);
      const saved = await fetchChartData(rec.id).catch(() => null);
      if (saved) {
        try {
          chartData.value = JSON.parse(saved) as ChartData;
        } catch {
          chartData.value = null;
        }
      } else {
        chartData.value = null;
      }
    } else {
      finalReport.value = null;
      chartData.value = null;
    }
  } catch {
    finalReport.value = null;
    chartData.value = null;
  }
});
</script>

<template>
  <div class="analysis-layout">
    <!-- Sidebar -->
    <WatchlistSidebar
      :items="watchlist"
      :selected="selectedStock"
      @select="onSelectStock"
      @add="onAddStock"
      @remove="onRemoveStock"
    />

    <!-- Main area -->
    <div class="main-area">
      <!-- Top bar -->
      <header class="topbar">
        <div class="stock-title">
          <span class="title-code">{{ selectedStock }}</span>
        </div>
        <div class="topbar-actions">
          <select class="ctrl-select" v-model="model">
            <option value="deepseek-chat">DeepSeek V4 Flash</option>
            <option value="deepseek-reasoner">DeepSeek V4 Pro</option>
          </select>
          <button
            class="ctrl-btn ctrl-btn-primary"
            @click="startAnalysis"
            :disabled="analyzing || !selectedStock"
          >
            {{ analyzing ? "分析中..." : "开始分析" }}
          </button>
          <button
            class="ctrl-btn"
            @click="showBacktestForm = true"
            :disabled="!selectedStock"
          >
            回测
          </button>
          <button class="ctrl-btn" @click="goHistory">历史分析</button>
          <button class="ctrl-btn" @click="goBacktestHistory">历史回测</button>
          <button class="ctrl-btn" @click="goVersions">版本</button>
        </div>
      </header>

      <!-- Content -->
      <div class="content">
        <!-- Same-symbol history bar -->
        <div class="history-bar" v-if="showHistory">
          <span class="history-bar-label">同标历史分析：</span>
          <button
            v-for="r in sameSymbolHistory"
            :key="r.id"
            class="history-chip"
            @click="router.push(`/history/${r.id}`)"
            :title="r.conclusion"
          >
            {{ new Date(r.created_at).toLocaleDateString("zh-CN") }}
          </button>
        </div>

        <!-- Chart -->
        <section class="card-glass chart-section" v-if="chartData">
          <div class="card-header">
            <h2>行情图表</h2>
          </div>
          <div class="chart-body">
            <KLineChart :data="chartData" />
          </div>
        </section>

        <!-- Report -->
        <section class="card-glass report-section" v-if="finalReport">
          <div class="card-header">
            <h2>技术分析报告</h2>
            <div class="report-actions">
              <button
                class="ctrl-btn ctrl-btn-sm"
                @click="
                  downloadReport(
                    analysisId || finalReport?.analysis_id || '',
                    'md'
                  )
                "
              >
                导出 Markdown
              </button>
              <button
                class="ctrl-btn ctrl-btn-sm"
                @click="
                  downloadReport(
                    analysisId || finalReport?.analysis_id || '',
                    'html'
                  )
                "
              >
                导出 HTML
              </button>
            </div>
          </div>
          <div class="report-body">
            <ReportViewer :report="finalReport" />
          </div>
        </section>

        <!-- Backtest result section -->
        <section class="card-glass backtest-section" v-if="backtestResult">
          <BacktestReport :result="backtestResult" />
        </section>

        <!-- Empty state -->
        <div class="empty-state" v-if="!chartData && !finalReport">
          <div class="empty-icon">📊</div>
          <p>选择自选股，点击"开始分析"</p>
          <p class="empty-hint">技术分析报告与行情图表将在此处展示</p>
        </div>
      </div>
    </div>

    <!-- Analysis Modal -->
    <AnalysisModal
      :visible="showAnalysisModal"
      :title="`技术分析 - ${selectedStock}`"
      :events="events"
      :analyzing="analyzing"
      :done="done"
      @close="closeAnalysis"
    />

    <!-- Backtest Form Modal -->
    <BacktestForm
      v-if="showBacktestForm"
      :symbol="selectedStock"
      @close="showBacktestForm = false"
      @result="
        (r) => {
          backtestResult = r;
          showBacktestForm = false;
        }
      "
    />

    <!-- Overwrite Confirmation Dialog -->
    <Teleport to="body">
      <div
        v-if="showOverwriteConfirm"
        class="modal-overlay"
        @click.self="showOverwriteConfirm = false"
      >
        <div class="modal-glass confirm-dialog">
          <div class="modal-header">
            <span class="modal-title">分析报告已存在</span>
          </div>
          <div class="confirm-body">
            <p>
              {{ selectedStock }} 在
              {{ pendingAnalysisDate }} 的分析报告已存在。
            </p>
            <p>是否重新计算并覆写历史版本？</p>
          </div>
          <div class="confirm-actions">
            <button
              class="ctrl-btn confirm-btn cancel"
              @click="cancelOverwrite"
            >
              取消 — 查看已有报告
            </button>
            <button
              class="ctrl-btn confirm-btn overwrite"
              @click="confirmOverwrite"
            >
              确认覆写
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.analysis-layout {
  display: flex;
  min-height: 100vh;
}

/* ─── Top Bar ─── */
.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 24px;
  background: var(--bg-glass);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border-bottom: 1px solid var(--glass-border);
  gap: 12px;
}
.stock-title {
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-shrink: 0;
}
.title-code {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 0.01em;
}
.topbar-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

/* ─── Controls ─── */
.ctrl-select {
  padding: 7px 32px 7px 12px;
  background: var(--bg-glass);
  border: 1px solid var(--glass-border);
  border-radius: 8px;
  color: var(--text-primary);
  font-size: 13px;
  font-family: inherit;
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg width='10' height='6' viewBox='0 0 10 6' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M1 1L5 5L9 1' stroke='%23888' stroke-width='1.5' stroke-linecap='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 10px center;
}
.ctrl-select:focus {
  outline: none;
  border-color: var(--accent-blue);
}
.ctrl-btn {
  padding: 7px 16px;
  background: var(--bg-glass);
  border: 1px solid var(--glass-border);
  border-radius: 8px;
  color: var(--text-secondary);
  font-size: 13px;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}
.ctrl-btn:hover {
  background: var(--bg-glass-hover);
  border-color: var(--glass-border-hover);
  color: var(--text-primary);
}
.ctrl-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.ctrl-btn-primary {
  background: linear-gradient(135deg, hsl(211, 90%, 52%), hsl(230, 70%, 48%));
  border-color: transparent;
  color: #fff;
  font-weight: 500;
}
.ctrl-btn-primary:hover {
  background: linear-gradient(135deg, hsl(211, 90%, 58%), hsl(230, 70%, 54%));
  color: #fff;
}
.ctrl-btn-primary:disabled {
  opacity: 0.5;
}
.ctrl-btn-sm {
  padding: 5px 12px;
  font-size: 12px;
}

/* ─── Confirmation Dialog ─── */
.confirm-dialog {
  width: 420px;
  max-width: 90vw;
}
.confirm-body {
  padding: 24px 22px;
  font-size: 14px;
  line-height: 1.6;
  color: var(--text-primary);
}
.confirm-body p {
  margin-bottom: 8px;
}
.confirm-actions {
  display: flex;
  gap: 10px;
  padding: 0 22px 22px;
}
.confirm-btn {
  flex: 1;
  padding: 9px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  text-align: center;
}
.confirm-btn.cancel {
  background: var(--bg-glass);
  border: 1px solid var(--glass-border);
  color: var(--text-secondary);
}
.confirm-btn.cancel:hover {
  background: var(--bg-glass-hover);
  color: var(--text-primary);
}
.confirm-btn.overwrite {
  background: linear-gradient(135deg, hsl(211, 90%, 52%), hsl(230, 70%, 48%));
  border: none;
  color: #fff;
}
.confirm-btn.overwrite:hover {
  background: linear-gradient(135deg, hsl(211, 90%, 58%), hsl(230, 70%, 54%));
}

/* ─── Content ─── */
.content {
  flex: 1;
  padding: 20px 24px 40px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
}

/* ─── History bar ─── */
.history-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--bg-glass);
  backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--glass-border);
  border-radius: 12px;
  padding: 10px 16px;
  flex-wrap: wrap;
}
.history-bar-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-muted);
  white-space: nowrap;
}
.history-chip {
  padding: 4px 12px;
  background: hsla(240, 14%, 20%, 0.4);
  border: 1px solid var(--glass-border);
  border-radius: 14px;
  font-size: 12px;
  cursor: pointer;
  color: var(--text-secondary);
  font-family: inherit;
  transition: all 0.2s;
}
.history-chip:hover {
  background: var(--bg-glass-hover);
  color: var(--text-primary);
  border-color: var(--glass-border-hover);
}

/* ─── Card glass ─── */
.card-glass {
  background: var(--bg-glass);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--glass-border);
  border-radius: 14px;
  box-shadow: var(--glass-shadow);
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 22px 0;
}
.card-header h2 {
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 0.01em;
}
.chart-body {
  padding: 4px 8px 8px;
}
.report-body {
  padding: 8px 22px 22px;
}
.report-actions {
  display: flex;
  gap: 6px;
}
.backtest-section {
  padding: 18px 22px;
}

/* ─── Empty state ─── */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 100px 0;
  text-align: center;
}
.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.4;
}
.empty-state p {
  color: var(--text-muted);
  font-size: 15px;
  margin-bottom: 6px;
}
.empty-hint {
  font-size: 13px !important;
  opacity: 0.7;
}
</style>

<!-- Non-scoped styles for Teleported modal content -->
<style>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: hsla(240, 18%, 4%, 0.7);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: confirmFadeIn 0.2s ease;
}
@keyframes confirmFadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}
.confirm-dialog {
  width: 460px;
  max-width: 90vw;
  background: hsla(240, 14%, 12%, 0.95);
  backdrop-filter: blur(32px);
  -webkit-backdrop-filter: blur(32px);
  border: 1px solid hsla(0, 0%, 100%, 0.08);
  border-radius: 18px;
  box-shadow: 0 24px 64px hsla(0, 0%, 0%, 0.6);
  overflow: hidden;
  animation: confirmModalIn 0.25s ease;
}
@keyframes confirmModalIn {
  from {
    opacity: 0;
    transform: scale(0.96) translateY(10px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}
.confirm-dialog .modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 22px 12px;
  border-bottom: 1px solid hsla(0, 0%, 100%, 0.06);
}
.confirm-dialog .modal-title {
  font-size: 16px;
  font-weight: 600;
  color: #f1f5f9;
}
.confirm-body {
  padding: 20px 22px;
}
.confirm-body p {
  color: #cbd5e1;
  font-size: 14px;
  line-height: 1.6;
  margin: 0 0 8px;
}
.confirm-actions {
  display: flex;
  gap: 10px;
  padding: 14px 22px 20px;
  justify-content: flex-end;
}
.confirm-btn {
  padding: 8px 18px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.15s ease;
}
.confirm-btn.cancel {
  background: hsla(0, 0%, 100%, 0.06);
  color: #94a3b8;
  border-color: hsla(0, 0%, 100%, 0.1);
}
.confirm-btn.cancel:hover {
  background: hsla(0, 0%, 100%, 0.1);
  color: #e2e8f0;
}
.confirm-btn.overwrite {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: #fff;
}
.confirm-btn.overwrite:hover {
  background: linear-gradient(135deg, #818cf8, #a78bfa);
  box-shadow: 0 4px 16px hsla(265, 80%, 60%, 0.3);
}
</style>
