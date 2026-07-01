<script setup lang="ts">
import { ref, watch } from "vue";
import AgentStream from "../components/AgentStream.vue";
import ReportViewer from "../components/ReportViewer.vue";
import { useSSE } from "../composables/useSSE";
import { useAnalysis } from "../composables/useAnalysis";
import type { AnalysisReport } from "../types";

const symbol = ref("600519");
const model = ref("deepseek-chat");
const analyzing = ref(false);
const finalReport = ref<AnalysisReport | null>(null);

const { events, done, analysisId, connect } = useSSE();
const { fetchReport } = useAnalysis();

watch(done, async (val) => {
  if (val && analysisId.value) {
    try {
      finalReport.value = await fetchReport(analysisId.value);
    } catch {
      // report may take a moment
    }
    analyzing.value = false;
  }
});

async function startAnalysis() {
  if (!symbol.value.trim()) return;
  analyzing.value = true;
  finalReport.value = null;

  const url = `/api/v1/analysis/start?symbol=${encodeURIComponent(symbol.value)}&model=${encodeURIComponent(model.value)}`;
  connect(url);
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
        </div>
      </div>
    </div>

    <div class="results-panel" v-if="events.length > 0 || finalReport">
      <section class="stream-section">
        <h2>执行过程</h2>
        <AgentStream :events="events" />
      </section>

      <section class="report-section" v-if="finalReport">
        <h2>分析报告</h2>
        <ReportViewer :report="finalReport" />
      </section>
    </div>

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
  margin-bottom: 24px;
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
