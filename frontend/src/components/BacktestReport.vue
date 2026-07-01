<script setup lang="ts">
import { computed } from "vue";
import type { BacktestResult } from "../types";
import { useBacktest } from "../composables/useBacktest";

const props = defineProps<{
  result: BacktestResult | null;
}>();

const { downloadBacktestReport } = useBacktest();

const resultData = computed(() => props.result);

const params = computed(() => {
  if (!props.result?.parameters) return null;
  return props.result.parameters;
});
</script>

<template>
  <div v-if="result" class="backtest-report">
    <div class="report-header">
      <h3>回测结果 - {{ result.symbol }}</h3>
      <button class="btn-export" @click="downloadBacktestReport(result)">
        导出报告
      </button>
    </div>

    <div class="metrics-grid" v-if="resultData">
      <div class="metric-card" v-if="resultData.initial_capital !== undefined">
        <div class="metric-label">初始资金</div>
        <div class="metric-value">
          {{ Number(resultData.initial_capital).toLocaleString() }}
        </div>
      </div>
      <div class="metric-card" v-if="resultData.final_capital !== undefined">
        <div class="metric-label">最终资金</div>
        <div class="metric-value">
          {{ Number(resultData.final_capital).toLocaleString() }}
        </div>
      </div>
      <div class="metric-card" v-if="resultData.total_return_pct !== undefined">
        <div class="metric-label">总收益率</div>
        <div
          class="metric-value"
          :class="
            Number(resultData.total_return_pct) >= 0 ? 'positive' : 'negative'
          "
        >
          {{ Number(resultData.total_return_pct).toFixed(2) }}%
        </div>
      </div>
      <div class="metric-card" v-if="resultData.max_drawdown_pct !== undefined">
        <div class="metric-label">最大回撤</div>
        <div class="metric-value negative">
          {{ Number(resultData.max_drawdown_pct).toFixed(2) }}%
        </div>
      </div>
      <div class="metric-card" v-if="resultData.win_rate !== undefined">
        <div class="metric-label">胜率</div>
        <div class="metric-value">
          {{ Number(resultData.win_rate).toFixed(1) }}%
        </div>
      </div>
      <div class="metric-card" v-if="resultData.total_trades !== undefined">
        <div class="metric-label">总交易次数</div>
        <div class="metric-value">{{ resultData.total_trades }}</div>
      </div>
    </div>

    <div class="params-info" v-if="params">
      <h4>回测参数</h4>
      <div class="params-grid">
        <span v-for="(v, k) in params" :key="String(k)">
          <strong>{{ k }}:</strong> {{ v }}
        </span>
      </div>
    </div>

    <div class="report-md" v-if="result.report_md">
      <h4>详细报告</h4>
      <pre>{{ result.report_md }}</pre>
    </div>
  </div>
  <div v-else class="empty-state">暂无回测结果</div>
</template>

<style scoped>
.backtest-report {
  background: transparent;
  padding: 0;
}
.report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.report-header h3 {
  font-size: 17px;
  color: var(--text-primary);
}
.btn-export {
  padding: 6px 16px;
  background: var(--bg-glass);
  border: 1px solid var(--glass-border);
  border-radius: 8px;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
}
.btn-export:hover {
  background: var(--bg-glass-hover);
  color: var(--text-primary);
}
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
.metric-card {
  background: hsla(240, 14%, 16%, 0.4);
  border: 1px solid var(--glass-border);
  border-radius: 8px;
  padding: 14px;
  text-align: center;
}
.metric-label {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 4px;
}
.metric-value {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
}
.metric-value.positive {
  color: var(--accent-green);
}
.metric-value.negative {
  color: var(--accent-red);
}
.params-info {
  margin-bottom: 16px;
}
.params-info h4 {
  font-size: 14px;
  margin-bottom: 8px;
  color: var(--text-secondary);
}
.params-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 13px;
  color: var(--text-muted);
}
.report-md h4 {
  font-size: 14px;
  margin-bottom: 8px;
  color: var(--text-secondary);
}
.report-md pre {
  background: hsla(240, 16%, 10%, 0.6);
  padding: 12px;
  border-radius: 8px;
  font-size: 13px;
  white-space: pre-wrap;
  max-height: 300px;
  overflow-y: auto;
  color: var(--text-secondary);
  border: 1px solid var(--glass-border);
}
.empty-state {
  text-align: center;
  padding: 40px;
  color: var(--text-muted);
}
</style>
