<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useBacktest } from "../composables/useBacktest";
import BacktestReport from "../components/BacktestReport.vue";
import type { BacktestResult } from "../types";

const route = useRoute();
const router = useRouter();
const { fetchBacktest } = useBacktest();
const result = ref<BacktestResult | null>(null);
const loading = ref(true);

onMounted(async () => {
  try {
    result.value = await fetchBacktest(route.params.id as string);
  } catch {
    // not found
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="detail-view">
    <button class="btn-back" @click="router.push('/backtest')">
      ← 返回回测历史
    </button>
    <div v-if="loading" class="loading">加载中...</div>
    <BacktestReport v-else-if="result" :result="result" />
    <div v-else class="not-found">
      <p>回测记录未找到</p>
      <button class="btn-back" @click="router.push('/backtest')">
        ← 返回回测历史
      </button>
    </div>
  </div>
</template>

<style scoped>
.detail-view {
  max-width: 900px;
  margin: 0 auto;
}
.btn-back {
  background: none;
  border: none;
  color: #1a1a2e;
  font-size: 14px;
  cursor: pointer;
  padding: 8px 0;
  margin-bottom: 16px;
}
.loading,
.not-found {
  text-align: center;
  padding: 40px;
  color: #999;
}
.not-found p {
  margin-bottom: 16px;
}
</style>
