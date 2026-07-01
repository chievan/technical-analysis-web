<script setup lang="ts">
import { RouterView, RouterLink } from "vue-router";
</script>

<template>
  <div class="app">
    <header class="app-header">
      <nav>
        <RouterLink to="/" class="logo">技术分析</RouterLink>
        <div class="nav-links">
          <RouterLink to="/">分析</RouterLink>
          <RouterLink to="/history">历史</RouterLink>
          <RouterLink to="/backtest">回测</RouterLink>
          <RouterLink to="/versions">版本</RouterLink>
        </div>
      </nav>
    </header>
    <main class="app-main">
      <RouterView />
    </main>
  </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
body {
  font-family:
    -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans SC",
    sans-serif;
  background: #f5f5f5;
  color: #333;
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
</style>
