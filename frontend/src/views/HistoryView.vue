<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useAnalysis } from "../composables/useAnalysis";
import type { AnalysisRecord } from "../types";

const router = useRouter();
const { fetchHistory } = useAnalysis();

const records = ref<AnalysisRecord[]>([]);
const loading = ref(true);
const symbolFilter = ref("");
const skillVersionFilter = ref("");

async function load() {
  loading.value = true;
  try {
    records.value = await fetchHistory({
      symbol: symbolFilter.value || undefined,
      skill_version: skillVersionFilter.value || undefined,
      limit: 50,
    });
  } finally {
    loading.value = false;
  }
}

function viewDetail(id: string) {
  router.push(`/history/${id}`);
}

const statusColors: Record<string, string> = {
  running: "#3b82f6",
  completed: "#22c55e",
  failed: "#ef4444",
  pending: "#888",
};

onMounted(load);
</script>

<template>
  <div class="history-view">
    <h1>历史记录</h1>

    <div class="filters">
      <input v-model="symbolFilter" placeholder="标的代码" @input="load" />
      <input
        v-model="skillVersionFilter"
        placeholder="Skill 版本"
        @input="load"
      />
    </div>

    <div v-if="loading" class="loading">加载中...</div>

    <div v-else-if="records.length === 0" class="empty">暂无分析记录</div>

    <div v-else class="record-list">
      <div
        v-for="r in records"
        :key="r.id"
        class="record-card"
        @click="viewDetail(r.id)"
      >
        <div class="record-header">
          <span class="symbol">{{ r.symbol }}</span>
          <span class="symbol-name" v-if="r.symbol_name"
            >({{ r.symbol_name }})</span
          >
          <span
            class="status-badge"
            :style="{ background: statusColors[r.status] || '#888' }"
          >
            {{ r.status }}
          </span>
        </div>
        <div class="record-meta">
          <span>模型: {{ r.model }}</span>
          <span>版本: {{ r.skill_version }}</span>
          <span>{{ new Date(r.created_at).toLocaleString("zh-CN") }}</span>
        </div>
        <div class="record-conclusion" v-if="r.conclusion">
          {{ r.conclusion }}
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.history-view {
  max-width: 900px;
  margin: 0 auto;
}
h1 {
  font-size: 24px;
  margin-bottom: 20px;
}
.filters {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}
.filters input {
  padding: 8px 12px;
  border: 1px solid #d0d0d0;
  border-radius: 6px;
  font-size: 14px;
  width: 200px;
}
.loading,
.empty {
  text-align: center;
  padding: 40px;
  color: #999;
}
.record-card {
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 12px;
  cursor: pointer;
  transition: box-shadow 0.2s;
}
.record-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}
.record-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.symbol {
  font-size: 18px;
  font-weight: 700;
}
.symbol-name {
  font-size: 14px;
  color: #666;
}
.status-badge {
  font-size: 11px;
  color: #fff;
  padding: 2px 8px;
  border-radius: 10px;
  text-transform: uppercase;
}
.record-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #888;
  margin-bottom: 8px;
}
.record-conclusion {
  font-size: 14px;
  color: #555;
  padding: 8px;
  background: #f5f5f5;
  border-radius: 4px;
}
</style>
