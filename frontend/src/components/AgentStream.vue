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

function eventContent(event: SSEEvent): string {
  if (event.type === "tool_call") {
    try {
      const data = JSON.parse(event.content);
      return (
        `🛠 调用工具: ${data.tool}` +
        (data.args ? `(${JSON.stringify(data.args)})` : "")
      );
    } catch {
      return `🛠 ${event.content}`;
    }
  }
  if (event.type === "tool_result") {
    try {
      const data = JSON.parse(event.content);
      return `✅ ${data.tool}: ${data.summary || "完成"}`;
    } catch {
      return `✅ ${event.content}`;
    }
  }
  return event.content;
}

function eventClass(type: string): string {
  return `step step--${type}`;
}
</script>

<template>
  <div class="agent-stream" ref="streamEl">
    <div v-if="events.length === 0" class="empty">等待分析开始...</div>
    <div v-for="(event, i) in events" :key="i" :class="eventClass(event.type)">
      <div class="step-label">
        <template v-if="event.type === 'thinking'">💭 思考</template>
        <template v-else-if="event.type === 'tool_call'">🛠 工具调用</template>
        <template v-else-if="event.type === 'tool_result'"
          >📊 工具结果</template
        >
        <template v-else-if="event.type === 'report_chunk'"
          >📝 报告片段</template
        >
        <template v-else-if="event.type === 'error'">⚠️ 错误</template>
      </div>
      <div class="step-content">
        {{ eventContent(event) }}
      </div>
      <div
        v-if="event.type === 'report_chunk'"
        class="step-markdown"
        v-html="event.content.replace(/\n/g, '<br>')"
      ></div>
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
.step-markdown {
  margin-top: 8px;
  padding: 8px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 4px;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
}
</style>
