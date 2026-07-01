<script setup lang="ts">
import { ref } from "vue";
import { useBacktest } from "../composables/useBacktest";
import type { BacktestResult } from "../types";

const props = defineProps<{
  symbol: string;
}>();

const emit = defineEmits<{
  close: [];
  result: [result: BacktestResult];
}>();

const { startBacktest, loading, error } = useBacktest();

const initialCapital = ref(100000);
const strategy = ref("trend_following");
const maShort = ref(5);
const maLong = ref(20);
const startDate = ref("");
const endDate = ref("");

async function submit() {
  try {
    const result = await startBacktest({
      symbol: props.symbol,
      start_date: startDate.value || undefined,
      end_date: endDate.value || undefined,
      initial_capital: initialCapital.value,
      strategy: strategy.value,
      ma_short: maShort.value,
      ma_long: maLong.value,
    });
    emit("result", result);
  } catch {
    // error is set in composable
  }
}
</script>

<template>
  <div class="modal-overlay" @click.self="emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h3>回测配置 - {{ symbol }}</h3>
        <button class="close-btn" @click="emit('close')">✕</button>
      </div>

      <div class="form-body">
        <div class="field-row">
          <div class="field">
            <label>开始日期（可选）</label>
            <input type="date" v-model="startDate" />
          </div>
          <div class="field">
            <label>结束日期（可选）</label>
            <input type="date" v-model="endDate" />
          </div>
        </div>
        <div class="field">
          <label>初始资金（元）</label>
          <input type="number" v-model.number="initialCapital" min="10000" />
        </div>
        <div class="field">
          <label>策略</label>
          <select v-model="strategy">
            <option value="trend_following">趋势跟踪（均线金叉/死叉）</option>
            <option value="mean_reversion">均值回归</option>
          </select>
        </div>
        <div class="field-row">
          <div class="field">
            <label>短期均线周期</label>
            <input type="number" v-model.number="maShort" min="2" max="50" />
          </div>
          <div class="field">
            <label>长期均线周期</label>
            <input type="number" v-model.number="maLong" min="10" max="200" />
          </div>
        </div>

        <div class="error-message" v-if="error">{{ error }}</div>
      </div>

      <div class="modal-footer">
        <button class="btn-cancel" @click="emit('close')">取消</button>
        <button class="btn-primary" @click="submit" :disabled="loading">
          {{ loading ? "回测中..." : "开始回测" }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
}
.modal-content {
  background: #fff;
  border-radius: 12px;
  width: 460px;
  max-width: 90vw;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px 0;
}
.modal-header h3 {
  font-size: 18px;
}
.close-btn {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  color: #888;
  padding: 4px 8px;
}
.close-btn:hover {
  color: #333;
}
.form-body {
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.field-row {
  display: flex;
  gap: 12px;
}
.field-row .field {
  flex: 1;
}
.field label {
  font-size: 13px;
  font-weight: 600;
  color: #666;
}
.field input,
.field select {
  padding: 8px 12px;
  border: 1px solid #d0d0d0;
  border-radius: 6px;
  font-size: 14px;
}
.error-message {
  color: #ef4444;
  font-size: 13px;
  padding: 8px 12px;
  background: #fef2f2;
  border-radius: 6px;
}
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 16px 24px 20px;
}
.btn-cancel {
  padding: 8px 20px;
  background: #f0f0f0;
  border: 1px solid #d0d0d0;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
}
.btn-primary {
  padding: 8px 24px;
  background: #1a1a2e;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
}
.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
