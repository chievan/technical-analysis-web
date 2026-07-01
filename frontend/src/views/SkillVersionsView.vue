<script setup lang="ts">
import { ref, onMounted } from "vue";

interface SkillVersionSummary {
  version: string;
  change_summary: string;
  created_at: string;
  files_count: number;
}

interface SkillVersionDetail {
  version: string;
  change_summary: string;
  created_at: string;
  files: Record<string, string>;
  files_count: number;
}

const versions = ref<SkillVersionSummary[]>([]);
const loading = ref(true);
const expanded = ref<string | null>(null);
const expandedDetail = ref<SkillVersionDetail | null>(null);
const detailLoading = ref(false);

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

async function toggleVersion(version: string) {
  if (expanded.value === version) {
    expanded.value = null;
    expandedDetail.value = null;
    return;
  }
  expanded.value = version;
  detailLoading.value = true;
  expandedDetail.value = null;
  try {
    const res = await fetch(
      `/api/v1/skill/versions/${encodeURIComponent(version)}`
    );
    if (res.ok) {
      expandedDetail.value = await res.json();
    }
  } catch {
    // ignore
  } finally {
    detailLoading.value = false;
  }
}
</script>

<template>
  <div class="skill-versions-view">
    <h1>Skill 版本历史</h1>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="versions.length === 0" class="empty">暂无版本记录</div>

    <div v-else class="version-list">
      <div
        v-for="v in versions"
        :key="v.version"
        class="version-card"
        :class="{ expanded: expanded === v.version }"
        @click="toggleVersion(v.version)"
      >
        <div class="version-header">
          <div class="version-left">
            <span class="version-tag">{{ v.version }}</span>
            <span class="version-date">
              {{ new Date(v.created_at).toLocaleString("zh-CN") }}
            </span>
          </div>
          <div class="version-meta">
            <span class="file-count">{{ v.files_count }} 个文件</span>
            <span class="expand-icon">{{
              expanded === v.version ? "▼" : "▶"
            }}</span>
          </div>
        </div>
        <div class="version-summary">{{ v.change_summary }}</div>

        <!-- Expanded detail -->
        <div v-if="expanded === v.version" class="version-detail" @click.stop>
          <div v-if="detailLoading" class="detail-loading">加载文件详情...</div>
          <div v-else-if="expandedDetail" class="detail-content">
            <h4>文件清单</h4>
            <div class="file-list">
              <div
                v-for="(hash, filename) in expandedDetail.files"
                :key="filename"
                class="file-row"
              >
                <span class="file-name">{{ filename }}</span>
                <code class="file-hash">{{ hash }}</code>
              </div>
            </div>
          </div>
        </div>
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
  gap: 8px;
}
.version-card {
  background: #fff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 14px 16px;
  cursor: pointer;
  transition: box-shadow 0.2s;
}
.version-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}
.version-card.expanded {
  border-color: #1a1a2e;
}
.version-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.version-left {
  display: flex;
  align-items: center;
  gap: 12px;
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
.version-meta {
  display: flex;
  align-items: center;
  gap: 10px;
}
.file-count {
  font-size: 12px;
  color: #999;
  background: #f0f0f0;
  padding: 2px 8px;
  border-radius: 8px;
}
.expand-icon {
  font-size: 11px;
  color: #aaa;
}
.version-summary {
  font-size: 13px;
  color: #666;
  margin-top: 8px;
  padding: 6px 10px;
  background: #f9f9f9;
  border-radius: 4px;
}
.version-detail {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #eee;
}
.detail-loading {
  text-align: center;
  padding: 20px;
  color: #999;
  font-size: 13px;
}
.detail-content h4 {
  font-size: 14px;
  margin-bottom: 8px;
  color: #333;
}
.file-list {
  max-height: 300px;
  overflow-y: auto;
}
.file-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 4px;
  font-size: 13px;
}
.file-row:nth-child(odd) {
  background: #f9f9f9;
}
.file-name {
  flex: 1;
  font-family: monospace;
  color: #333;
}
.file-hash {
  font-family: monospace;
  font-size: 11px;
  background: #f0f0f0;
  padding: 2px 6px;
  border-radius: 3px;
  color: #888;
}
</style>
