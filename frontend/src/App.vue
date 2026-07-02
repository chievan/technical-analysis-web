<script setup lang="ts">
import { computed } from "vue";
import { RouterView, RouterLink, useRoute } from "vue-router";

const route = useRoute();
const isHome = computed(() => route.path === "/");
</script>

<template>
  <div class="app">
    <header v-if="!isHome" class="app-header">
      <nav>
        <RouterLink to="/" class="logo">技术分析</RouterLink>
        <div class="nav-links">
          <RouterLink to="/">分析</RouterLink>
          <RouterLink to="/history">历史</RouterLink>
          <RouterLink to="/backtest">回测</RouterLink>
          <RouterLink to="/versions">版本</RouterLink>
          <RouterLink to="/skill-editor">策略</RouterLink>
        </div>
      </nav>
    </header>
    <main class="app-main" :class="{ 'app-main--full': isHome }">
      <RouterView />
    </main>
  </div>
</template>

<style>
/* ─── Design System Tokens ─── */
:root {
  --bg-primary: hsl(240, 18%, 6%);
  --bg-surface: hsla(240, 14%, 14%, 0.65);
  --bg-sidebar: hsla(240, 16%, 10%, 0.92);
  --bg-glass: hsla(240, 14%, 16%, 0.55);
  --bg-glass-hover: hsla(240, 14%, 20%, 0.65);
  --glass-border: hsla(0, 0%, 100%, 0.07);
  --glass-border-hover: hsla(0, 0%, 100%, 0.14);
  --glass-shadow: 0 8px 32px hsla(0, 0%, 0%, 0.4);
  --glass-blur: 20px;

  --accent-green: hsl(142, 76%, 45%);
  --accent-red: hsl(0, 76%, 52%);
  --accent-blue: hsl(211, 90%, 52%);
  --accent-gold: hsl(42, 96%, 52%);
  --accent-purple: hsl(262, 70%, 58%);

  --text-primary: hsl(0, 0%, 90%);
  --text-secondary: hsla(0, 0%, 100%, 0.6);
  --text-muted: hsla(0, 0%, 100%, 0.35);
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
body {
  font-family:
    "Inter",
    -apple-system,
    BlinkMacSystemFont,
    "Segoe UI",
    "Noto Sans SC",
    sans-serif;
  background: hsl(240, 18%, 6%);
  color: hsl(0, 0%, 90%);
  min-height: 100vh;
}
.app-header {
  background: #1a1a2e;
  color: #fff;
  padding: 0 24px;
  position: sticky;
  top: 0;
  z-index: 100;
}
.app-header nav {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  height: 56px;
  gap: 32px;
}
.logo {
  font-size: 18px;
  font-weight: 700;
  color: #fff;
  text-decoration: none;
}
.nav-links {
  display: flex;
  gap: 16px;
}
.nav-links a {
  color: #ccc;
  text-decoration: none;
  font-size: 15px;
}
.nav-links a:hover,
.nav-links a.router-link-exact-active {
  color: #fff;
}
.app-main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}
.app-main--full {
  max-width: none;
  margin: 0;
  padding: 0;
}
</style>
