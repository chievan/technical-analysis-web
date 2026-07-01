<script setup lang="ts">
import { ref, onMounted } from "vue";

export interface WatchlistItem {
  code: string;
  name: string;
}

const props = defineProps<{
  items: WatchlistItem[];
  selected: string;
}>();

const emit = defineEmits<{
  select: [code: string];
  add: [code: string];
  remove: [code: string];
}>();

const showSearch = ref(false);
const searchQuery = ref("");

/** Known stock lookup (for demo; in production would hit an API). */
const knownStocks: WatchlistItem[] = [
  { code: "000300", name: "沪深300" },
  { code: "600519", name: "贵州茅台" },
  { code: "600909", name: "华安证券" },
  { code: "600036", name: "招商银行" },
  { code: "000001", name: "平安银行" },
  { code: "601318", name: "中国平安" },
  { code: "600900", name: "长江电力" },
  { code: "000858", name: "五粮液" },
  { code: "TL", name: "30年期国债期货" },
  { code: "T", name: "10年期国债期货" },
];

const searchResults = ref<WatchlistItem[]>([]);

function onSearchInput() {
  if (!searchQuery.value.trim()) {
    searchResults.value = [];
    return;
  }
  const q = searchQuery.value.toUpperCase();
  searchResults.value = knownStocks.filter(
    (s) => s.code.includes(q) || s.name.includes(q)
  );
}

function addStock(item: WatchlistItem) {
  emit("add", item.code);
  showSearch.value = false;
  searchQuery.value = "";
  searchResults.value = [];
}
</script>

<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <span class="sidebar-logo">技术分析</span>
    </div>

    <div class="watchlist-section">
      <div class="section-label">自选股</div>

      <div
        v-for="item in items"
        :key="item.code"
        class="watchlist-item"
        :class="{ active: item.code === selected }"
        @click="emit('select', item.code)"
      >
        <span class="stock-code">{{ item.code }}</span>
        <span class="stock-name">{{ item.name }}</span>
        <button
          v-if="item.code !== selected"
          class="remove-btn"
          @click.stop="emit('remove', item.code)"
          title="删除"
        >
          ✕
        </button>
      </div>

      <button class="add-btn" @click="showSearch = true">
        <span class="add-icon">+</span> 添加自选
      </button>
    </div>

    <!-- Search overlay -->
    <Teleport to="body">
      <div
        v-if="showSearch"
        class="search-overlay"
        @click.self="showSearch = false"
      >
        <div class="search-panel">
          <div class="search-header">
            <span>添加自选股</span>
            <button class="search-close" @click="showSearch = false">✕</button>
          </div>
          <input
            v-model="searchQuery"
            class="search-input"
            placeholder="输入标的代码或名称"
            @input="onSearchInput"
            autofocus
          />
          <div v-if="searchResults.length > 0" class="search-results">
            <div
              v-for="r in searchResults"
              :key="r.code"
              class="search-result-item"
              @click="addStock(r)"
            >
              <span class="sr-code">{{ r.code }}</span>
              <span class="sr-name">{{ r.name }}</span>
            </div>
          </div>
          <div
            v-else-if="searchQuery && searchResults.length === 0"
            class="search-empty"
          >
            未匹配到标的
          </div>
        </div>
      </div>
    </Teleport>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 260px;
  min-width: 260px;
  background: hsla(240, 16%, 10%, 0.92);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-right: 1px solid hsla(0, 0%, 100%, 0.07);
  display: flex;
  flex-direction: column;
  height: 100vh;
  position: sticky;
  top: 0;
}
.sidebar-header {
  padding: 20px 18px 14px;
  border-bottom: 1px solid hsla(0, 0%, 100%, 0.07);
}
.sidebar-logo {
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: hsl(0, 0%, 90%);
}
.watchlist-section {
  padding: 14px 10px;
  flex: 1;
  overflow-y: auto;
}
.section-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: hsla(0, 0%, 100%, 0.35);
  padding: 0 8px 10px;
}
.watchlist-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 11px 12px;
  margin: 2px 0;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}
.watchlist-item:hover {
  background: hsla(240, 14%, 20%, 0.5);
}
.watchlist-item.active {
  background: linear-gradient(
    135deg,
    hsla(211, 90%, 52%, 0.15),
    hsla(230, 70%, 48%, 0.08)
  );
  border: 1px solid hsla(211, 90%, 52%, 0.2);
}
.stock-code {
  font-size: 14px;
  font-weight: 600;
  color: hsl(0, 0%, 90%);
  font-family: "SF Mono", "Menlo", monospace;
}
.stock-name {
  font-size: 12px;
  color: hsla(0, 0%, 100%, 0.35);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.remove-btn {
  width: 20px;
  height: 20px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: hsla(0, 0%, 100%, 0.25);
  font-size: 11px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: all 0.2s;
}
.watchlist-item:hover .remove-btn {
  opacity: 1;
}
.remove-btn:hover {
  background: hsla(0, 76%, 52%, 0.2);
  color: hsl(0, 76%, 52%);
}
.add-btn {
  width: 100%;
  margin-top: 12px;
  padding: 10px;
  background: hsla(240, 14%, 16%, 0.55);
  border: 1px dashed hsla(0, 0%, 100%, 0.07);
  border-radius: 10px;
  color: hsla(0, 0%, 100%, 0.35);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  font-family: inherit;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}
.add-btn:hover {
  border-color: hsl(211, 90%, 52%);
  color: hsl(211, 90%, 52%);
  background: hsla(211, 90%, 52%, 0.08);
}
.add-icon {
  font-size: 16px;
  font-weight: 600;
}

/* Search overlay */
.search-overlay {
  position: fixed;
  inset: 0;
  background: hsla(240, 18%, 4%, 0.6);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 80px;
  z-index: 2000;
}
.search-panel {
  width: 400px;
  background: hsla(240, 14%, 12%, 0.95);
  backdrop-filter: blur(24px);
  border: 1px solid hsla(0, 0%, 100%, 0.1);
  border-radius: 14px;
  box-shadow: 0 20px 60px hsla(0, 0%, 0%, 0.5);
  overflow: hidden;
  animation: slideDown 0.2s ease;
}
@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
.search-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 18px 8px;
  font-size: 14px;
  font-weight: 600;
  color: hsl(0, 0%, 90%);
}
.search-close {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 6px;
  background: hsla(240, 14%, 16%, 0.55);
  color: hsla(0, 0%, 100%, 0.45);
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}
.search-close:hover {
  background: hsla(0, 76%, 52%, 0.2);
  color: hsl(0, 76%, 52%);
}
.search-input {
  width: 100%;
  padding: 12px 18px;
  background: transparent;
  border: none;
  border-bottom: 1px solid hsla(0, 0%, 100%, 0.07);
  color: hsl(0, 0%, 90%);
  font-size: 15px;
  font-family: inherit;
  outline: none;
}
.search-input::placeholder {
  color: hsla(0, 0%, 100%, 0.3);
}
.search-results {
  max-height: 240px;
  overflow-y: auto;
}
.search-result-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 18px;
  cursor: pointer;
  transition: background 0.15s;
}
.search-result-item:hover {
  background: hsla(240, 14%, 20%, 0.5);
}
.sr-code {
  font-size: 14px;
  font-weight: 600;
  color: hsl(0, 0%, 90%);
  font-family: "SF Mono", "Menlo", monospace;
}
.sr-name {
  font-size: 13px;
  color: hsla(0, 0%, 100%, 0.45);
}
.search-empty {
  padding: 24px;
  text-align: center;
  color: hsla(0, 0%, 100%, 0.3);
  font-size: 13px;
}
</style>
