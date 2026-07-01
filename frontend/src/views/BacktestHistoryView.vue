<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useBacktest } from "../composables/useBacktest";
import type { BacktestResult } from "../types";

const router = useRouter();
const { fetchBacktestHistory } = useBacktest();
const records = ref<BacktestResult[]>([]);
const loading = ref(true);
const symbolFilter = ref("");
const dateFrom = ref("");
const dateTo = ref("");

async function load() {
  loading.value = true;
  try {
    records.value = await fetchBacktestHistory({
      symbol: symbolFilter.value || undefined,
      date_from: dateFrom.value || undefined,
      date_to: dateTo.value || undefined,
      limit: 50,
    });
  } finally {
    loading.value = false;
  }
}

function viewDetail(r: BacktestResult) {
  router.push(`/backtest/${r.id}`);
}

onMounted(load);
</script>

<template>
  <div class="backtest-history-view">
    <h1>回测历史</h1>
    <div class="filters">
      <input v-model="symbolFilter" placeholder="标的代码" @input="load" />
      <input type="date" v-model="dateFrom" @input="load" />
      <input type="date" v-model="dateTo" @input="load" />
    </div>
    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="records.length === 0" class="empty">暂无回测记录</div>
    <div v-else class="record-list">
      <div
        v-for="r in records"
        :key="r.id"
        class="record-card"
        @click="viewDetail(r)"
      >
        <div class="record-header">
          <span class="symbol">{{ r.symbol }}</span>
          <span class="date">{{
            new Date(r.created_at).toLocaleString("zh-CN")
          }}</span>
        </div>
        <div class="record-meta">
          <span
            >收益率:
            {{
              r.total_return_pct != null
                ? r.total_return_pct.toFixed(2) + "%"
                : "?"
            }}</span
          >
          <span
            >最大回撤:
            {{
              r.max_drawdown_pct != null
                ? r.max_drawdown_pct.toFixed(2) + "%"
                : "?"
            }}</span
          >
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.backtest-history-view {
  max-width: 900px;
  margin: 0 auto;
}
h1 {
  font-size: 24px;
  margin-bottom: 20px;
}
.filters {
  margin-bottom: 20px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.filters input {
  padding: 8px 12px;
  border: 1px solid #d0d0d0;
  border-radius: 6px;
  font-size: 14px;
  width: 200px;
}
.filters input[type="date"] {
  width: 160px;
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
  gap: 12px;
  margin-bottom: 8px;
}
.symbol {
  font-size: 18px;
  font-weight: 700;
}
.date {
  font-size: 13px;
  color: #888;
}
.record-meta {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: #666;
}
</style>
