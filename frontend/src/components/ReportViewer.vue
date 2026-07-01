<script setup lang="ts">
import { computed } from "vue";
import type { AnalysisReport } from "../types";

const props = defineProps<{
  report: AnalysisReport | null;
}>();

const rendered = computed(() => {
  if (!props.report) return "";
  // Convert markdown-like content to basic HTML
  let html = props.report.report_md;
  // Headers
  html = html.replace(/^### (.+)$/gm, "<h3>$1</h3>");
  html = html.replace(/^## (.+)$/gm, "<h2>$1</h2>");
  // Bold
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  // Table rows
  html = html.replace(/^\|(.+)\|$/gm, (row: string) => {
    if (row.includes("---")) return '<hr class="table-divider">';
    const cells = row
      .split("|")
      .filter((c) => c.trim())
      .map((c) => `<td>${c.trim()}</td>`)
      .join("");
    return `<tr>${cells}</tr>`;
  });
  // Wrap tables
  if (html.includes("<tr>")) {
    html = html.replace(/(<tr>.*<\/tr>)/gs, "<table>$1</table>");
  }
  // Lists
  html = html.replace(/^(\d+)\. (.+)$/gm, "<li>$2</li>");
  // Line breaks
  html = html.replace(/\n\n/g, "</p><p>");
  html = html.replace(/\n/g, "<br>");
  return `<p>${html}</p>`;
});
</script>

<template>
  <div class="report-viewer" v-if="report">
    <div class="report-content" v-html="rendered"></div>
  </div>
  <div v-else class="empty-report">暂无报告</div>
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
.report-content :deep(td) {
  padding: 8px 12px;
  border: 1px solid #ddd;
  text-align: left;
}
.report-content :deep(hr.table-divider) {
  display: none;
}
.report-content :deep(li) {
  margin-bottom: 6px;
  margin-left: 20px;
}
.empty-report {
  text-align: center;
  padding: 40px;
  color: #999;
}
</style>
