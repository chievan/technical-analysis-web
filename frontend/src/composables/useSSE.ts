import { ref, onUnmounted } from "vue";
import type { SSEEvent } from "../types";

export function useSSE() {
  const events = ref<SSEEvent[]>([]);
  const connected = ref(false);
  const done = ref(false);
  const analysisId = ref<string | null>(null);
  const chartDataStr = ref<string>("");
  let source: EventSource | null = null;

  function connect(url: string) {
    disconnect();
    events.value = [];
    done.value = false;
    chartDataStr.value = "";
    connected.value = true;

    source = new EventSource(url);

    source.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as SSEEvent;
        events.value.push(data);

        // Accumulate chart_data for the K-line chart
        if (data.type === "chart_data" && data.content) {
          chartDataStr.value = data.content;
        }

        if (data.type === "done") {
          done.value = true;
          analysisId.value = data.analysis_id || null;
          disconnect();
        }
      } catch {
        // skip malformed messages
      }
    };

    source.onerror = () => {
      connected.value = false;
      disconnect();
    };
  }

  function disconnect() {
    if (source) {
      source.close();
      source = null;
    }
    connected.value = false;
  }

  onUnmounted(() => disconnect());

  return {
    events,
    connected,
    done,
    analysisId,
    chartDataStr,
    connect,
    disconnect,
  };
}
