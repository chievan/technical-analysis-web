<script setup lang="ts">
import { computed, ref, watch, nextTick } from "vue";
import type { SSEEvent } from "../types";

const props = defineProps<{
  events: SSEEvent[];
}>();

const streamEl = ref<HTMLElement | null>(null);

watch(
  () => props.events.length,
  async () => {
    await nextTick();
    if (streamEl.value) {
      streamEl.value.scrollTop = streamEl.value.scrollHeight;
    }
  }
);

/** Merge consecutive same-type events (especially thinking) into groups. */
const groupedEvents = computed(() => {
  const groups: { type: string; content: string }[] = [];
  for (const ev of props.events) {
    if (
      ev.type === "thinking" &&
      groups.length > 0 &&
      groups[groups.length - 1].type === "thinking"
    ) {
      groups[groups.length - 1].content += ev.content;
    } else {
      groups.push({ type: ev.type, content: ev.content });
    }
  }
  return groups;
});

function tryJsonParse(s: string): Record<string, unknown> | null {
  try {
    return JSON.parse(s) as Record<string, unknown>;
  } catch {
    return null;
  }
}

function eventClass(type: string): string {
  return `step step--${type}`;
}

function toolLabel(tool: string): string {
  const labels: Record<string, string> = {
    run_ta_engine: "技术分析引擎",
    read_reference: "参考文档",
    run_backtester: "回测引擎",
  };
  return labels[tool] || tool;
}

function displayContent(event: { type: string; content: string }): {
  label: string;
  body: string;
} {
  if (event.type === "tool_call") {
    const data = tryJsonParse(event.content);
    if (data) {
      const tool = (data.tool as string) || "";
      const args = data.args as Record<string, string> | undefined;
      return {
        label: `🛠 工具调用 - ${toolLabel(tool)}`,
        body: args ? `参数: ${JSON.stringify(args)}` : "",
      };
    }
    return { label: "🛠 工具调用", body: event.content };
  }
  if (event.type === "tool_result") {
    const data = tryJsonParse(event.content);
    if (data) {
      const tool = (data.tool as string) || "";
      const summary = (data.summary as string) || "完成";
      return {
        label: `📊 工具结果 - ${toolLabel(tool)}`,
        body: summary,
      };
    }
    return { label: "📊 工具结果", body: event.content };
  }
  if (event.type === "report_chunk")
    return { label: "📝 报告片段", body: event.content };
  if (event.type === "report_complete")
    return { label: "✅ 报告完成", body: "" };
  if (event.type === "chart_data")
    return { label: "📈 图表数据已就绪", body: "K线图数据已加载，准备渲染" };
  if (event.type === "thinking")
    return { label: "💭 思考", body: event.content };
  if (event.type === "error") return { label: "⚠️ 错误", body: event.content };
  return { label: event.type, body: event.content };
}
</script>

<template>
  <div class="agent-stream" ref="streamEl">
    <div v-if="events.length === 0" class="empty">等待分析开始...</div>
    <div
      v-for="(event, i) in groupedEvents"
      :key="i"
      :class="eventClass(event.type)"
    >
      <div class="step-label">{{ displayContent(event).label }}</div>
      <div class="step-content">{{ displayContent(event).body }}</div>
    </div>
  </div>
</template>

<style scoped>
.agent-stream {
  background: #1a1a2e;
  color: #e0e0e0;
  border-radius: 8px;
  padding: 16px;
  max-height: 500px;
  overflow-y: auto;
  font-family: "Menlo", "Consolas", monospace;
  font-size: 13px;
  line-height: 1.6;
}
.empty {
  color: #888;
  text-align: center;
  padding: 40px 0;
}
.step {
  margin-bottom: 12px;
  padding: 8px 12px;
  border-radius: 6px;
}
.step--thinking {
  background: rgba(255, 255, 255, 0.05);
}
.step--tool_call {
  background: rgba(59, 130, 246, 0.15);
  border-left: 3px solid #3b82f6;
}
.step--tool_result {
  background: rgba(34, 197, 94, 0.15);
  border-left: 3px solid #22c55e;
}
.step--report_chunk {
  background: rgba(234, 179, 8, 0.1);
  border-left: 3px solid #eab308;
}
.step--error {
  background: rgba(239, 68, 68, 0.15);
  border-left: 3px solid #ef4444;
}
.step--error .step-content {
  color: #fca5a5;
}
.step-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  margin-bottom: 4px;
  opacity: 0.7;
}
.step-content {
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
