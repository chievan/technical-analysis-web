<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount } from "vue";
import { Codemirror } from "vue-codemirror";
import { basicSetup } from "codemirror";
import { EditorView } from "@codemirror/view";
import { markdown } from "@codemirror/lang-markdown";
import { python } from "@codemirror/lang-python";
import { oneDark } from "@codemirror/theme-one-dark";

import SkillFileTree, { type SkillFileNode } from "./SkillFileTree.vue";

// Vite dev proxy forwards /api → localhost:8000
const API_BASE = "";

const files = ref<SkillFileNode[]>([]);
const activePath = ref<string | null>(null);
const dirtyPaths = ref<Set<string>>(new Set());
const editorContent = ref("");
const loading = ref(true);
const saving = ref(false);
const currentHash = ref("");
const toastMsg = ref("");
const toastType = ref<"success" | "error" | "info">("info");
const toastVisible = ref(false);

let toastTimer: ReturnType<typeof setTimeout> | null = null;

const activeFile = computed(
  () => files.value.find((f) => f.path === activePath.value) ?? null
);

const editorExtensions = computed(() => {
  const lang = activeFile.value?.language;
  const langExt =
    lang === "python" ? python() : lang === "markdown" ? markdown() : [];
  return [basicSetup, EditorView.lineWrapping, oneDark, langExt];
});

const isDirty = computed(() => dirtyPaths.value.size > 0);

function showToast(msg: string, type: "success" | "error" | "info" = "info") {
  toastMsg.value = msg;
  toastType.value = type;
  toastVisible.value = true;
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    toastVisible.value = false;
  }, 4000);
}

async function fetchFiles() {
  loading.value = true;
  try {
    const res = await fetch(`${API_BASE}/api/v1/skill/files`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    files.value = data.files;
    currentHash.value = data.hash;
    if (!activePath.value && data.files.length > 0) {
      selectFile(data.files[0].path);
    }
  } catch (err: any) {
    showToast(`Failed to load files: ${err.message}`, "error");
  } finally {
    loading.value = false;
  }
}

function selectFile(path: string) {
  // Save current editor content before switching
  if (activePath.value && activePath.value !== path) {
    const f = files.value.find((x) => x.path === activePath.value);
    if (f && dirtyPaths.value.has(f.path)) {
      f.content = editorContent.value;
    }
  }
  activePath.value = path;
  const f = files.value.find((x) => x.path === path);
  editorContent.value = f?.content ?? "";
}

function onContentChange(val: string) {
  editorContent.value = val;
  if (activePath.value) {
    dirtyPaths.value.add(activePath.value);
  }
}

async function saveAll() {
  if (!isDirty.value) return;
  saving.value = true;

  const changedFiles = files.value
    .filter((f) => dirtyPaths.value.has(f.path))
    .map((f) => ({ path: f.path, content: f.content }));

  try {
    const res = await fetch(`${API_BASE}/api/v1/skill/files`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        files: changedFiles,
        expected_hash: currentHash.value,
      }),
    });

    if (res.status === 409) {
      const err = await res.json();
      showToast(
        `Conflict: ${err.detail?.message ?? "files changed externally. Reloading..."}`,
        "error"
      );
      await fetchFiles();
      return;
    }

    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const result = await res.json();
    dirtyPaths.value.clear();
    currentHash.value = "";
    showToast(
      `Saved — v${result.version}${result.commit_sha ? ` (${result.commit_sha.slice(0, 7)})` : ""}`,
      "success"
    );

    // Refresh to get new hash
    await fetchFiles();
  } catch (err: any) {
    showToast(`Save failed: ${err.message}`, "error");
  } finally {
    saving.value = false;
  }
}

async function resetAll() {
  if (!isDirty.value) return;
  dirtyPaths.value.clear();
  // Reload to get original content
  showToast("Changes discarded", "info");
  await fetchFiles();
}

// Warn before leaving with unsaved changes
function handleBeforeUnload(e: BeforeUnloadEvent) {
  if (dirtyPaths.value.size > 0) {
    e.preventDefault();
  }
}
onMounted(() => {
  window.addEventListener("beforeunload", handleBeforeUnload);
  fetchFiles();
});
onBeforeUnmount(() => {
  window.removeEventListener("beforeunload", handleBeforeUnload);
  if (toastTimer) clearTimeout(toastTimer);
});
</script>

<template>
  <div class="skill-editor">
    <div class="editor-sidebar">
      <div class="sidebar-header">
        <span class="sidebar-title">Skill 文件</span>
      </div>
      <SkillFileTree
        :files="files"
        :active-path="activePath"
        :dirty-paths="dirtyPaths"
        :loading="loading"
        @select-file="selectFile"
      />
      <div class="sidebar-actions">
        <button
          class="btn-save"
          :disabled="!isDirty || saving"
          @click="saveAll"
        >
          {{ saving ? "保存中..." : "保存全部" }}
        </button>
        <button class="btn-reset" :disabled="!isDirty" @click="resetAll">
          重置
        </button>
      </div>
    </div>
    <div class="editor-main">
      <div v-if="loading" class="editor-loading">Loading editor...</div>
      <div v-else-if="!activeFile" class="editor-empty">
        选择一个文件开始编辑
      </div>
      <div v-else class="editor-pane">
        <div class="editor-toolbar">
          <span class="editor-path">{{ activeFile.path }}</span>
          <span class="editor-lang">{{ activeFile.language }}</span>
        </div>
        <Codemirror
          v-model="editorContent"
          :extensions="editorExtensions"
          :autofocus="true"
          :disabled="false"
          :indent-with-tab="true"
          :tab-size="2"
          :style="{ height: '100%' }"
          @update:model-value="onContentChange"
        />
      </div>
    </div>
    <Transition name="toast">
      <div v-if="toastVisible" class="toast" :class="`toast--${toastType}`">
        {{ toastMsg }}
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.skill-editor {
  display: flex;
  height: calc(100vh - 56px);
  position: relative;
}

/* ─── Sidebar ─── */
.editor-sidebar {
  width: 280px;
  min-width: 280px;
  background: var(--bg-sidebar);
  border-right: 1px solid var(--glass-border);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}
.sidebar-header {
  padding: 12px 16px;
  border-bottom: 1px solid var(--glass-border);
  font-size: 13px;
  font-weight: 600;
  color: var(--text-primary);
  letter-spacing: 0.02em;
  text-transform: uppercase;
}
.sidebar-actions {
  padding: 12px;
  border-top: 1px solid var(--glass-border);
  display: flex;
  gap: 8px;
  margin-top: auto;
}
.btn-save,
.btn-reset {
  flex: 1;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  transition: opacity 0.2s;
}
.btn-save {
  background: var(--accent-blue);
  color: #fff;
  border: none;
}
.btn-save:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.btn-reset {
  background: transparent;
  color: var(--text-secondary);
  border-color: var(--glass-border);
}
.btn-reset:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}
.btn-reset:not(:disabled):hover {
  background: var(--bg-glass-hover);
  color: var(--text-primary);
}

/* ─── Editor ─── */
.editor-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: hsl(240, 18%, 6%);
}
.editor-loading,
.editor-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-muted);
  font-size: 14px;
}
.editor-pane {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.editor-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 16px;
  background: hsla(240, 14%, 12%, 0.8);
  border-bottom: 1px solid var(--glass-border);
  font-size: 12px;
}
.editor-path {
  color: var(--text-secondary);
  font-family: "SF Mono", Menlo, monospace;
}
.editor-lang {
  color: var(--text-muted);
  background: var(--bg-glass);
  padding: 2px 8px;
  border-radius: 4px;
  text-transform: uppercase;
  font-size: 11px;
}

/* Codemirror overrides */
.editor-pane :deep(.v-codemirror) {
  flex: 1;
  overflow: auto;
}
.editor-pane :deep(.cm-editor) {
  height: 100%;
}
.editor-pane :deep(.cm-scroller) {
  font-family: "SF Mono", Menlo, Consolas, monospace;
  font-size: 13px;
}

/* ─── Toast ─── */
.toast {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  padding: 10px 20px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 500;
  z-index: 9999;
  pointer-events: none;
  backdrop-filter: blur(12px);
}
.toast--success {
  background: hsla(142, 76%, 45%, 0.2);
  border: 1px solid hsla(142, 76%, 45%, 0.3);
  color: var(--accent-green);
}
.toast--error {
  background: hsla(0, 76%, 52%, 0.2);
  border: 1px solid hsla(0, 76%, 52%, 0.3);
  color: var(--accent-red);
}
.toast--info {
  background: hsla(211, 90%, 52%, 0.15);
  border: 1px solid hsla(211, 90%, 52%, 0.25);
  color: var(--accent-blue);
}
.toast-enter-active,
.toast-leave-active {
  transition:
    opacity 0.3s,
    transform 0.3s;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(12px);
}
</style>
