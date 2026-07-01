<script setup lang="ts">
import { ref, onMounted } from "vue";

interface SkillVersion {
  version: string;
  change_summary: string;
  created_at: string;
}

const versions = ref<SkillVersion[]>([]);
const loading = ref(true);

onMounted(async () => {
  try {
    const res = await fetch("/api/v1/skill/versions");
    versions.value = await res.json();
  } catch {
    // ignore
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="skill-versions-view">
    <h1>Skill 版本历史</h1>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="versions.length === 0" class="empty">暂无版本记录</div>

    <div v-else class="version-list">
      <div v-for="v in versions" :key="v.version" class="version-card">
        <div class="version-header">
          <span class="version-tag">{{ v.version }}</span>
          <span class="version-date">
            {{ new Date(v.created_at).toLocaleString("zh-CN") }}
          </span>
        </div>
        <div class="version-summary">{{ v.change_summary }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.skill-versions-view {
  max-width: 900px;
  margin: 0 auto;
}
h1 {
  font-size: 24px;
  margin-bottom: 20px;
}
.loading,
.empty {
  text-align: center;
  padding: 40px;
  color: #999;
}
.version-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.version-card {
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 16px;
}
.version-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}
.version-tag {
  display: inline-block;
  padding: 3px 10px;
  background: #1a1a2e;
  color: #fff;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  font-family: monospace;
}
.version-date {
  font-size: 13px;
  color: #888;
}
.version-summary {
  font-size: 14px;
  color: #555;
  padding: 8px;
  background: #f5f5f5;
  border-radius: 4px;
}
</style>
