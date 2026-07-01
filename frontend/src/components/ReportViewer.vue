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
  background: transparent;
  padding: 0;
}
.report-content {
  line-height: 1.8;
  font-size: 15px;
  color: var(--text-primary);
}
.report-content :deep(h1) {
  font-size: 24px;
  margin: 28px 0 14px;
  padding-bottom: 10px;
  border-bottom: 2px solid hsl(211, 90%, 52%);
  color: var(--text-primary);
}
.report-content :deep(h2) {
  font-size: 20px;
  margin: 24px 0 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--glass-border);
  color: var(--text-primary);
}
.report-content :deep(h3) {
  font-size: 17px;
  margin: 20px 0 10px;
  color: var(--text-primary);
}
.report-content :deep(p) {
  margin-bottom: 12px;
  color: var(--text-secondary);
}
.report-content :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
}
.report-content :deep(th),
.report-content :deep(td) {
  padding: 8px 12px;
  border: 1px solid var(--glass-border);
  text-align: left;
  color: var(--text-secondary);
}
.report-content :deep(th) {
  background: hsla(240, 14%, 16%, 0.5);
  font-weight: 600;
  color: var(--text-primary);
}
.report-content :deep(ul),
.report-content :deep(ol) {
  margin: 12px 0;
  padding-left: 24px;
  color: var(--text-secondary);
}
.report-content :deep(li) {
  margin-bottom: 6px;
}
.report-content :deep(code) {
  background: hsla(240, 14%, 16%, 0.6);
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 13px;
  color: var(--accent-gold);
}
.report-content :deep(pre) {
  background: hsla(240, 16%, 10%, 0.8);
  color: #e0e0e0;
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 16px 0;
  border: 1px solid var(--glass-border);
}
.report-content :deep(blockquote) {
  border-left: 4px solid var(--accent-blue);
  padding-left: 16px;
  margin: 16px 0;
  color: var(--text-secondary);
  opacity: 0.85;
}
.report-content :deep(a) {
  color: var(--accent-blue);
  text-decoration: none;
}
.report-content :deep(a:hover) {
  text-decoration: underline;
}
.report-content :deep(hr) {
  border: none;
  border-top: 1px solid var(--glass-border);
  margin: 20px 0;
}
.report-content :deep(img) {
  max-width: 100%;
  border-radius: 8px;
}
.empty-report {
  text-align: center;
  padding: 40px;
  color: var(--text-muted);
}
</style>
