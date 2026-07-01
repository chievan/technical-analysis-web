import { ref, onUnmounted } from "vue";
import type { SSEEvent } from "../types";

export function useSSE() {
  const events = ref<SSEEvent[]>([]);
  const connected = ref(false);
  const done = ref(false);
  const error = ref<string | null>(null);
  const analysisId = ref<string | null>(null);
  const chartDataStr = ref<string>("");
  const backtestResultStr = ref<string>("");
  let source: EventSource | null = null;
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  let reconnectAttempts = 0;
  const MAX_RECONNECT_ATTEMPTS = 5;
  const INITIAL_RECONNECT_DELAY = 1000;
  let currentUrl = "";
  let manuallyClosed = false;

  function connect(url: string) {
    disconnect();
    events.value = [];
    done.value = false;
    error.value = null;
    chartDataStr.value = "";
    backtestResultStr.value = "";
    reconnectAttempts = 0;
    manuallyClosed = false;
    currentUrl = url;
    doConnect();
  }

  function doConnect() {
    if (!currentUrl || manuallyClosed) return;
    if (source) source.close();

    connected.value = true;
    source = new EventSource(currentUrl);

    source.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as SSEEvent;
        events.value.push(data);

        if (data.type === "chart_data" && data.content) {
          chartDataStr.value = data.content;
        }
        if (data.type === "backtest_result" && data.content) {
          backtestResultStr.value = data.content;
        }
        if (data.type === "error") {
          error.value = data.content;
        }
        if (data.type === "done") {
          done.value = true;
          analysisId.value = data.analysis_id || null;
          manuallyClosed = true;
          disconnect();
        }
      } catch {
        // skip malformed messages
      }
    };

    source.onerror = () => {
      connected.value = false;
      // Auto reconnect with exponential backoff if not done and not manually closed
      if (!manuallyClosed && reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
        reconnectAttempts++;
        const delay =
          INITIAL_RECONNECT_DELAY * Math.pow(2, reconnectAttempts - 1);
        reconnectTimer = setTimeout(() => {
          doConnect();
        }, delay);
      } else if (!manuallyClosed) {
        error.value = "连接已断开，请刷新页面重试";
      }
    };
  }

  function disconnect() {
    manuallyClosed = true;
    if (source) {
      source.close();
      source = null;
    }
    if (reconnectTimer) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    connected.value = false;
  }

  onUnmounted(() => disconnect());

  return {
    events,
    connected,
    done,
    error,
    analysisId,
    chartDataStr,
    backtestResultStr,
    connect,
    disconnect,
  };
}
