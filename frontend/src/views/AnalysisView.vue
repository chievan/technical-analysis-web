<script setup lang="ts">
import { ref, watch } from "vue";
import AgentStream from "../components/AgentStream.vue";
import ReportViewer from "../components/ReportViewer.vue";
import KLineChart from "../components/KLineChart.vue";
import BacktestForm from "../components/BacktestForm.vue";
import BacktestReport from "../components/BacktestReport.vue";
import type { ChartData } from "../types";
import { useSSE } from "../composables/useSSE";
import { useAnalysis } from "../composables/useAnalysis";
import type { AnalysisRecord, AnalysisReport, BacktestResult } from "../types";

const symbol = ref("600519");
const model = ref("deepseek-chat");
const analyzing = ref(false);
const finalReport = ref<AnalysisReport | null>(null);
const chartData = ref<ChartData | null>(null);
const sameSymbolHistory = ref<AnalysisRecord[]>([]);
const showHistory = ref(false);
const showBacktestForm = ref(false);
const backtestResult = ref<BacktestResult | null>(null);

const { events, done, error, analysisId, chartDataStr, connect } = useSSE();
const { fetchReport, fetchHistory, fetchChartData, downloadReport } =
  useAnalysis();

// Parse chart_data JSON string → object
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
    try {
      finalReport.value = await fetchReport(analysisId.value);
      // If chart data didn't come via SSE, try fetching from saved report
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
      // report may take a moment, set error for user feedback
      error.value = "分析报告加载失败，请尝试重新分析";
    }
    analyzing.value = false;
  }
});

// Load same-symbol history when a report is available
watch(finalReport, async (report) => {
  if (report) {
    try {
      const records = await fetchHistory({ symbol: symbol.value, limit: 5 });
      // Filter out the current analysis
      sameSymbolHistory.value = records.filter(
        (r) => r.id !== analysisId.value
      );
      showHistory.value = sameSymbolHistory.value.length > 0;
    } catch {
      sameSymbolHistory.value = [];
    }
  }
});

async function startAnalysis() {
  if (!symbol.value.trim()) return;
  analyzing.value = true;
  finalReport.value = null;
  chartData.value = null;
  sameSymbolHistory.value = [];
  showHistory.value = false;

  const url = `/api/v1/analysis/start?symbol=${encodeURIComponent(symbol.value)}&model=${encodeURIComponent(model.value)}`;
  connect(url);
}

function loadHistorical(id: string) {
  // Navigate to history detail page
  window.open(`/history/${id}`, "_blank");
}
</script>

<template>
  <div class="analysis-view">
    <h1>技术分析</h1>

    <div class="control-panel">
      <div class="control-row">
        <div class="field">
          <label for="symbol">标的代码</label>
          <input
            id="symbol"
            v-model="symbol"
            placeholder="如 600519、000300、TL"
            :disabled="analyzing"
          />
        </div>
        <div class="field">
          <label for="model">模型</label>
          <select id="model" v-model="model" :disabled="analyzing">
            <option value="deepseek-chat">DeepSeek V4 Flash</option>
            <option value="deepseek-reasoner">DeepSeek V4 Pro</option>
          </select>
        </div>
        <div class="field">
          <label>&nbsp;</label>
          <button
            class="btn-primary"
            @click="startAnalysis"
            :disabled="analyzing || !symbol.trim()"
          >
            {{ analyzing ? "分析中..." : "开始分析" }}
          </button>
          <button
            class="btn-backtest"
            @click="showBacktestForm = true"
            :disabled="!symbol.trim()"
            v-if="!analyzing"
          >
            回测
          </button>
        </div>
      </div>
    </div>

    <!-- Same-symbol history bar -->
    <div class="history-bar" v-if="showHistory">
      <span class="history-bar-label">同标历史分析：</span>
      <button
        v-for="r in sameSymbolHistory"
        :key="r.id"
        class="history-chip"
        @click="loadHistorical(r.id)"
        :title="r.conclusion"
      >
        {{ new Date(r.created_at).toLocaleDateString("zh-CN") }}
        <span class="chip-status" :class="r.status">{{ r.status }}</span>
      </button>
    </div>

    <div class="error-banner" v-if="error">
      <span>{{ error }}</span>
      <button class="btn-retry" @click="startAnalysis">重试</button>
    </div>

    <div class="results-panel" v-if="events.length > 0 || finalReport">
      <section class="stream-section">
        <h2>执行过程</h2>
        <AgentStream :events="events" />
      </section>

      <!-- Chart section -->
      <section class="chart-section" v-if="chartData">
        <h2>交互图表</h2>
        <KLineChart :data="chartData" />
      </section>

      <section class="report-section" v-if="finalReport">
        <h2>分析报告</h2>
        <div class="report-actions">
          <button
            class="btn-export"
            @click="downloadReport(analysisId || '', 'md')"
          >
            导出 Markdown
          </button>
          <button
            class="btn-export"
            @click="downloadReport(analysisId || '', 'html')"
          >
            导出 HTML
          </button>
        </div>
        <ReportViewer :report="finalReport" />
      </section>
    </div>

    <!-- Backtest report section -->
    <section class="backtest-section" v-if="backtestResult">
      <h2>回测结果</h2>
      <BacktestReport :result="backtestResult" />
    </section>

    <!-- Backtest form modal -->
    <BacktestForm
      v-if="showBacktestForm"
      :symbol="symbol"
      @close="showBacktestForm = false"
      @result="
        (r) => {
          backtestResult = r;
          showBacktestForm = false;
        }
      "
    />

    <div class="empty-state" v-else>
      <p>输入标的代码，选择模型，点击"开始分析"查看技术分析流程。</p>
    </div>
  </div>
</template>

<style scoped>
.analysis-view {
  max-width: 900px;
  margin: 0 auto;
}
h1 {
  font-size: 24px;
  margin-bottom: 20px;
}
.control-panel {
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 12px;
}
.control-row {
  display: flex;
  gap: 16px;
  align-items: flex-end;
  flex-wrap: wrap;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.field label {
  font-size: 13px;
  font-weight: 600;
  color: #666;
}
.field input,
.field select {
  padding: 8px 12px;
  border: 1px solid #d0d0d0;
  border-radius: 6px;
  font-size: 14px;
  min-width: 180px;
}
.btn-primary {
  padding: 8px 24px;
  background: #1a1a2e;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  white-space: nowrap;
}
.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn-backtest {
  padding: 8px 20px;
  background: #fff;
  color: #1a1a2e;
  border: 1px solid #1a1a2e;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  white-space: nowrap;
}
.btn-backtest:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.error-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  color: #dc2626;
  font-size: 14px;
  margin-bottom: 12px;
}
.btn-retry {
  padding: 4px 12px;
  background: #dc2626;
  color: #fff;
  border: none;
  border-radius: 4px;
  font-size: 13px;
  cursor: pointer;
}
.backtest-section {
  margin-top: 24px;
}
.backtest-section h2 {
  font-size: 18px;
  margin-bottom: 12px;
}
.history-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 10px 16px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.history-bar-label {
  font-size: 13px;
  font-weight: 600;
  color: #888;
  white-space: nowrap;
}
.history-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: #f0f0f0;
  border: 1px solid #ddd;
  border-radius: 12px;
  font-size: 12px;
  cursor: pointer;
  color: #333;
}
.history-chip:hover {
  background: #e0e0e0;
}
.chip-status {
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 8px;
  color: #fff;
}
.chip-status.completed {
  background: #22c55e;
}
.chip-status.failed {
  background: #ef4444;
}
.chip-status.running {
  background: #3b82f6;
}
.report-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
.btn-export {
  padding: 6px 16px;
  background: #1a1a2e;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
}
.btn-export:hover {
  opacity: 0.9;
}
.results-panel section {
  margin-bottom: 24px;
}
.results-panel h2 {
  font-size: 18px;
  margin-bottom: 12px;
}
.empty-state {
  text-align: center;
  padding: 80px 0;
  color: #999;
  font-size: 16px;
}
</style>
