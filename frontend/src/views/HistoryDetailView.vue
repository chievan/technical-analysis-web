<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import ReportViewer from "../components/ReportViewer.vue";
import { useAnalysis } from "../composables/useAnalysis";
import type { AnalysisRecord, AnalysisReport } from "../types";

const route = useRoute();
const router = useRouter();
const { fetchAnalysis, fetchReport } = useAnalysis();

const analysis = ref<AnalysisRecord | null>(null);
const report = ref<AnalysisReport | null>(null);
const loading = ref(true);

onMounted(async () => {
  try {
    const id = route.params.id as string;
    analysis.value = await fetchAnalysis(id);
    report.value = await fetchReport(id);
  } catch {
    // report not found
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
      </div>

      <section class="report-section">
        <h2>分析报告</h2>
        <ReportViewer :report="report" />
      </section>
    </template>
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
}
.conclusion {
  padding: 12px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 6px;
  font-size: 14px;
  color: #166534;
}
.report-section h2 {
  font-size: 18px;
  margin-bottom: 12px;
}
</style>
