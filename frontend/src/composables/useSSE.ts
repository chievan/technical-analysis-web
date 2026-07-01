import { ref, onUnmounted } from "vue";
import type { SSEEvent } from "../types";

export function useSSE() {
  const events = ref<SSEEvent[]>([]);
  const connected = ref(false);
  const done = ref(false);
  const analysisId = ref<string | null>(null);
  let source: EventSource | null = null;

  function connect(url: string) {
    disconnect();
    events.value = [];
    done.value = false;
    connected.value = true;

    source = new EventSource(url);

    source.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as SSEEvent;
        events.value.push(data);

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

  return { events, connected, done, analysisId, connect, disconnect };
}
