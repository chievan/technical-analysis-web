<script setup lang="ts">
import { computed } from "vue";
import { marked } from "marked";
import type { AnalysisReport } from "../types";

const props = defineProps<{
  report: AnalysisReport | null;
}>();

const rendered = computed(() => {
  if (!props.report) return "";
  try {
    return marked(props.report.report_md, { async: false }) as string;
  } catch {
    // Fallback: basic line-by-line rendering if marked fails
    return props.report.report_md
      .split("\n")
      .map((line) => `<p>${line}</p>`)
      .join("");
  }
});
</script>

<template>
  <div class="report-viewer" v-if="report && report.report_md">
    <div class="report-content" v-html="rendered"></div>
  </div>
  <div v-else class="empty-report">暂无分析结果</div>
</template>

<style scoped>
.report-viewer {
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 24px;
}
.report-content {
  line-height: 1.8;
  font-size: 15px;
}
.report-content :deep(h1) {
  font-size: 24px;
  margin: 28px 0 14px;
  padding-bottom: 10px;
  border-bottom: 2px solid #1a1a2e;
}
.report-content :deep(h2) {
  font-size: 20px;
  margin: 24px 0 12px;
  padding-bottom: 8px;
  border-bottom: 2px solid #1a1a2e;
}
.report-content :deep(h3) {
  font-size: 17px;
  margin: 20px 0 10px;
}
.report-content :deep(p) {
  margin-bottom: 12px;
}
.report-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
}
.report-content :deep(th),
.report-content :deep(td) {
  padding: 8px 12px;
  border: 1px solid #ddd;
  text-align: left;
}
.report-content :deep(th) {
  background: #f5f5f5;
  font-weight: 600;
}
.report-content :deep(ul),
.report-content :deep(ol) {
  margin: 12px 0;
  padding-left: 24px;
}
.report-content :deep(li) {
  margin-bottom: 6px;
}
.report-content :deep(code) {
  background: #f0f0f0;
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 13px;
}
.report-content :deep(pre) {
  background: #1a1a2e;
  color: #e0e0e0;
  padding: 16px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 16px 0;
}
.report-content :deep(blockquote) {
  border-left: 4px solid #1a1a2e;
  padding-left: 16px;
  margin: 16px 0;
  color: #666;
}
.empty-report {
  text-align: center;
  padding: 40px;
  color: #999;
}
</style>
