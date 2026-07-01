<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import ReportViewer from "../components/ReportViewer.vue";
import KLineChart from "../components/KLineChart.vue";
import BacktestReport from "../components/BacktestReport.vue";
import type { ChartData, BacktestResult } from "../types";
import { useAnalysis } from "../composables/useAnalysis";
import { useBacktest } from "../composables/useBacktest";
import type { AnalysisRecord, AnalysisReport } from "../types";

const route = useRoute();
const router = useRouter();
const { fetchAnalysis, fetchReport, fetchChartData, downloadReport } =
  useAnalysis();
const { fetchBacktestHistory, fetchBacktest } = useBacktest();

const analysis = ref<AnalysisRecord | null>(null);
const report = ref<AnalysisReport | null>(null);
const chartData = ref<ChartData | null>(null);
const loading = ref(true);
const loadError = ref<string | null>(null);
const backtestRecords = ref<BacktestResult[]>([]);
const backtestLoading = ref(false);

onMounted(async () => {
  try {
    const id = route.params.id as string;
    analysis.value = await fetchAnalysis(id);
    report.value = await fetchReport(id);

    // Load chart data from saved report
    const saved = await fetchChartData(id);
    if (saved) {
      try {
        chartData.value = JSON.parse(saved) as ChartData;
      } catch {
        /* not chart data */
      }
    }

    // Load backtest history for this symbol (fetch full details for each)
    if (analysis.value) {
      backtestLoading.value = true;
      try {
        const summary = await fetchBacktestHistory({
          symbol: analysis.value.symbol,
          limit: 5,
        });
        // Fetch full details for each backtest record
        const details = await Promise.all(
          summary.map((r) => fetchBacktest(r.id).catch(() => null))
        );
        backtestRecords.value = details.filter(Boolean) as BacktestResult[];
      } catch {
        backtestRecords.value = [];
      } finally {
        backtestLoading.value = false;
      }
    }
  } catch (e) {
    loadError.value = e instanceof Error ? e.message : "加载失败，请返回重试";
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="detail-view">
    <button class="btn-back" @click="router.push('/history')">
      ← 返回历史
    </button>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else-if="loadError" class="error-banner">
      <span>{{ loadError }}</span>
      <button class="btn-back" @click="router.push('/history')">
        ← 返回历史
      </button>
    </div>

    <template v-else-if="analysis">
      <div class="analysis-info">
        <h1>{{ analysis.symbol }} {{ analysis.symbol_name }}</h1>
        <div class="meta">
          <span>模型: {{ analysis.model }}</span>
          <span>版本: {{ analysis.skill_version }}</span>
          <span>状态: {{ analysis.status }}</span>
          <span>{{
            new Date(analysis.created_at).toLocaleString("zh-CN")
          }}</span>
        </div>
        <div v-if="analysis.conclusion" class="conclusion">
          {{ analysis.conclusion }}
        </div>

        <!-- Export buttons -->
        <div class="export-actions" v-if="report">
          <button class="btn-export" @click="downloadReport(analysis.id, 'md')">
            导出 Markdown
          </button>
          <button
            class="btn-export"
            @click="downloadReport(analysis.id, 'html')"
          >
            导出 HTML
          </button>
        </div>
      </div>

      <!-- Chart section -->
      <section class="chart-section" v-if="chartData">
        <h2>交互图表</h2>
        <KLineChart :data="chartData" />
      </section>

      <section class="report-section">
        <h2>分析报告</h2>
        <ReportViewer :report="report" />
      </section>

      <!-- Backtest history section -->
      <section class="backtest-section" v-if="backtestRecords.length > 0">
        <h2>历史回测</h2>
        <div v-if="backtestLoading" class="loading">加载中...</div>
        <div v-else class="backtest-list">
          <BacktestReport
            v-for="r in backtestRecords"
            :key="r.id"
            :result="r"
          />
        </div>
      </section>
    </template>

    <div v-else class="not-found">
      <p>分析记录未找到</p>
      <button class="btn-back" @click="router.push('/history')">
        ← 返回历史
      </button>
    </div>
  </div>
</template>

<style scoped>
.detail-view {
  max-width: 900px;
  margin: 0 auto;
}
.btn-back {
  background: none;
  border: none;
  color: #1a1a2e;
  font-size: 14px;
  cursor: pointer;
  padding: 8px 0;
  margin-bottom: 16px;
}
.btn-back:hover {
  text-decoration: underline;
}
.loading {
  text-align: center;
  padding: 40px;
  color: #999;
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
.not-found {
  text-align: center;
  padding: 60px 0;
  color: #999;
}
.analysis-info {
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 24px;
  margin-bottom: 24px;
}
.analysis-info h1 {
  font-size: 22px;
  margin-bottom: 12px;
}
.meta {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: #888;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.conclusion {
  padding: 12px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 6px;
  font-size: 14px;
  color: #166534;
  margin-bottom: 12px;
}
.export-actions {
  display: flex;
  gap: 8px;
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
.chart-section h2 {
  font-size: 18px;
  margin-bottom: 12px;
}
.report-section h2 {
  font-size: 18px;
  margin-bottom: 12px;
}
.backtest-section {
  margin-top: 24px;
}
.backtest-section h2 {
  font-size: 18px;
  margin-bottom: 12px;
}
.backtest-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
</style>
