<script setup lang="ts">
import { ref, watch, nextTick } from "vue";
import type { SSEEvent } from "../types";

const props = defineProps<{
  visible: boolean;
  title: string;
  events: SSEEvent[];
  analyzing: boolean;
  done: boolean;
}>();

const emit = defineEmits<{
  close: [];
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

function eventLabel(event: SSEEvent): string {
  switch (event.type) {
    case "thinking":
      return "💭 深度思考";
    case "tool_call":
      return "🛠 工具调用";
    case "tool_result":
      return "📊 工具结果";
    case "report_chunk":
      return "📝 报告片段";
    case "report_complete":
      return "✅ 分析完成";
    case "chart_data":
      return "📈 图表数据已就绪";
    case "error":
      return "⚠️ 错误";
    default:
      return event.type;
  }
}

function tryJsonParse(s: string): Record<string, unknown> | null {
  try {
    return JSON.parse(s) as Record<string, unknown>;
  } catch {
    return null;
  }
}

function eventBody(event: SSEEvent): string {
  if (event.type === "tool_call") {
    const data = tryJsonParse(event.content);
    return data ? JSON.stringify(data.args || {}, null, 2) : event.content;
  }
  if (event.type === "tool_result") {
    const data = tryJsonParse(event.content);
    return data?.summary ? String(data.summary) : event.content;
  }
  return event.content;
}
</script>

<template>
  <Teleport to="body">
    <div v-if="visible" class="modal-overlay" @click.self="emit('close')">
      <div class="modal-glass">
        <div class="modal-header">
          <div class="modal-title-area">
            <span class="modal-status-icon">
              {{ done ? "✅" : analyzing ? "🔄" : "✅" }}
            </span>
            <span class="modal-title">{{ title }}</span>
          </div>
          <button class="modal-close" @click="emit('close')" title="关闭">
            ✕
          </button>
        </div>

        <div class="modal-body" ref="streamEl">
          <!-- Waiting state -->
          <div v-if="events.length === 0 && analyzing" class="state-waiting">
            <div class="pulse-dot"></div>
            <span>正在连接分析引擎...</span>
          </div>

          <!-- Stream events -->
          <div
            v-for="(ev, i) in events"
            :key="i"
            class="stream-step"
            :class="'step--' + ev.type"
          >
            <div class="step-label">{{ eventLabel(ev) }}</div>
            <div class="step-body">{{ eventBody(ev) }}</div>
          </div>

          <!-- Done state -->
          <div v-if="done" class="state-done">
            <span>分析已完成，可关闭此窗口查看结果</span>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: hsla(240, 18%, 4%, 0.7);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s ease;
}
@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}
.modal-glass {
  width: 620px;
  max-width: 92vw;
  max-height: 80vh;
  background: hsla(240, 14%, 12%, 0.92);
  backdrop-filter: blur(32px);
  -webkit-backdrop-filter: blur(32px);
  border: 1px solid hsla(0, 0%, 100%, 0.07);
  border-radius: 18px;
  box-shadow: 0 24px 64px hsla(0, 0%, 0%, 0.6);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: modalIn 0.25s ease;
}
@keyframes modalIn {
  from {
    opacity: 0;
    transform: scale(0.96) translateY(10px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 22px;
  border-bottom: 1px solid hsla(0, 0%, 100%, 0.07);
}
.modal-title-area {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 15px;
  font-weight: 600;
  color: hsl(0, 0%, 90%);
}
.modal-status-icon {
  font-size: 18px;
}
.modal-close {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: hsla(240, 14%, 16%, 0.55);
  border: 1px solid hsla(0, 0%, 100%, 0.07);
  color: hsla(0, 0%, 100%, 0.45);
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}
.modal-close:hover {
  background: hsla(0, 76%, 52%, 0.2);
  border-color: hsl(0, 76%, 52%);
  color: hsl(0, 76%, 52%);
}
.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 16px 22px 22px;
}
.state-waiting {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 40px 0;
  color: hsla(0, 0%, 100%, 0.45);
  font-size: 14px;
  justify-content: center;
}
.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: hsl(211, 90%, 52%);
  animation: pulse 1.2s ease-in-out infinite;
}
@keyframes pulse {
  0%,
  100% {
    opacity: 0.3;
    transform: scale(0.8);
  }
  50% {
    opacity: 1;
    transform: scale(1.2);
  }
}
.stream-step {
  margin-bottom: 10px;
  padding: 10px 14px;
  border-radius: 10px;
  background: hsla(240, 14%, 16%, 0.4);
  border-left: 3px solid hsla(0, 0%, 100%, 0.07);
  animation: stepIn 0.3s ease;
}
@keyframes stepIn {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
.step--thinking {
  border-left-color: hsl(42, 96%, 52%);
  background: hsla(42, 96%, 52%, 0.06);
}
.step--tool_call {
  border-left-color: hsl(211, 90%, 52%);
  background: hsla(211, 90%, 52%, 0.08);
}
.step--tool_result {
  border-left-color: hsl(142, 76%, 45%);
  background: hsla(142, 76%, 45%, 0.06);
}
.step--report_chunk {
  border-left-color: hsl(262, 70%, 58%);
  background: hsla(262, 70%, 58%, 0.06);
}
.step--report_complete,
.step--done {
  border-left-color: hsl(142, 76%, 45%);
  background: hsla(142, 76%, 45%, 0.1);
}
.step--error {
  border-left-color: hsl(0, 76%, 52%);
  background: hsla(0, 76%, 52%, 0.08);
}
.step-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.03em;
  color: hsla(0, 0%, 100%, 0.6);
  margin-bottom: 4px;
}
.step-body {
  font-size: 13px;
  line-height: 1.6;
  color: hsl(0, 0%, 90%);
  white-space: pre-wrap;
}
.state-done {
  text-align: center;
  padding: 18px;
  color: hsl(142, 76%, 45%);
  font-size: 14px;
  font-weight: 500;
}
</style>
