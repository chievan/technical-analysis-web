<script setup lang="ts">
import { computed } from "vue";

export interface SkillFileNode {
  path: string;
  type: "file";
  language: string;
  content: string;
}

const props = defineProps<{
  files: SkillFileNode[];
  activePath: string | null;
  dirtyPaths: Set<string>;
  loading: boolean;
}>();

const emit = defineEmits<{
  selectFile: [path: string];
}>();

interface TreeNode {
  name: string;
  path: string;
  isDir: boolean;
  children: TreeNode[];
}

const tree = computed<TreeNode[]>(() => {
  const root: TreeNode[] = [];
  const map = new Map<string, TreeNode>();

  for (const f of props.files) {
    const parts = f.path.split("/");
    let current = root;
    let accumulated = "";

    for (let i = 0; i < parts.length; i++) {
      const isLast = i === parts.length - 1;
      accumulated = accumulated ? `${accumulated}/${parts[i]}` : parts[i];
      const existing = map.get(accumulated);
      if (existing) {
        current = existing.children;
      } else {
        const node: TreeNode = {
          name: parts[i],
          path: accumulated,
          isDir: !isLast,
          children: [],
        };
        map.set(accumulated, node);
        current.push(node);
        current = node.children;
      }
    }
  }
  return root;
});

function toggleDir(node: TreeNode) {
  if (node.isDir) {
    node.children = node.children.length ? node.children : node.children;
  }
}

function selectFile(node: TreeNode) {
  if (!node.isDir) {
    emit("selectFile", node.path);
  }
}
</script>

<template>
  <div class="file-tree">
    <div v-if="loading" class="tree-loading">
      <div
        v-for="i in 3"
        :key="i"
        class="skeleton-row"
        :style="{ width: `${60 + i * 20}px` }"
      />
    </div>
    <div v-else-if="files.length === 0" class="tree-empty">
      No skill files found
    </div>
    <ul v-else class="tree-list">
      <li v-for="node in tree" :key="node.path" class="tree-item">
        <div v-if="node.isDir" class="tree-folder" @click="toggleDir(node)">
          <span class="tree-icon">📁</span>
          <span class="tree-label folder-label">{{ node.name }}/</span>
        </div>
        <div
          v-else
          class="tree-file"
          :class="{ active: activePath === node.path }"
          @click="selectFile(node)"
        >
          <span
            v-if="dirtyPaths.has(node.path)"
            class="dirty-dot"
            title="Unsaved changes"
          />
          <span class="tree-icon">{{ iconFor(node.path) }}</span>
          <span class="tree-label">{{ node.name }}</span>
        </div>
        <ul v-if="node.isDir && node.children.length" class="tree-children">
          <li
            v-for="child in node.children"
            :key="child.path"
            class="tree-item"
          >
            <div
              class="tree-file"
              :class="{ active: activePath === child.path }"
              @click="selectFile(child)"
            >
              <span
                v-if="dirtyPaths.has(child.path)"
                class="dirty-dot"
                title="Unsaved changes"
              />
              <span class="tree-icon">{{ iconFor(child.path) }}</span>
              <span class="tree-label">{{ child.name }}</span>
            </div>
          </li>
        </ul>
      </li>
    </ul>
  </div>
</template>

<script lang="ts">
function iconFor(path: string): string {
  if (path.endsWith(".md")) return "📄";
  if (path.endsWith(".py")) return "🐍";
  if (path.endsWith(".json")) return "📋";
  return "📄";
}
</script>

<style scoped>
.file-tree {
  padding: 8px 0;
  user-select: none;
}
.tree-loading {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.skeleton-row {
  height: 14px;
  border-radius: 4px;
  background: hsla(240, 14%, 20%, 0.6);
}
.tree-empty {
  padding: 24px 16px;
  color: var(--text-muted);
  font-size: 13px;
  text-align: center;
}
.tree-list {
  list-style: none;
  padding: 0;
  margin: 0;
}
.tree-children {
  list-style: none;
  padding: 0 0 0 20px;
  margin: 0;
}
.tree-item {
  margin: 0;
}
.tree-folder {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  font-size: 13px;
  color: var(--text-secondary);
  cursor: default;
}
.tree-file {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px 6px 32px;
  font-size: 13px;
  color: var(--text-secondary);
  cursor: pointer;
  border-left: 2px solid transparent;
  transition:
    background 0.15s,
    color 0.15s,
    border-color 0.15s;
}
.tree-file:hover {
  background: var(--bg-glass-hover);
  color: var(--text-primary);
}
.tree-file.active {
  color: var(--text-primary);
  background: hsla(211, 90%, 52%, 0.12);
  border-left-color: var(--accent-blue);
}
.tree-icon {
  font-size: 14px;
  line-height: 1;
}
.tree-label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.folder-label {
  font-weight: 600;
  color: var(--text-primary);
}
.dirty-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent-gold);
  flex-shrink: 0;
}
</style>
