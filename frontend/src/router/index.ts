import { createRouter, createWebHistory } from "vue-router";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "analysis",
      component: () => import("../views/AnalysisView.vue"),
    },
    {
      path: "/history",
      name: "history",
      component: () => import("../views/HistoryView.vue"),
    },
    {
      path: "/history/:id",
      name: "history-detail",
      component: () => import("../views/HistoryDetailView.vue"),
    },
    {
      path: "/backtest",
      name: "backtest-history",
      component: () => import("../views/BacktestHistoryView.vue"),
    },
    {
      path: "/backtest/:id",
      name: "backtest-detail",
      component: () => import("../views/BacktestDetailView.vue"),
    },
    {
      path: "/versions",
      name: "skill-versions",
      component: () => import("../views/SkillVersionsView.vue"),
    },
  ],
});

export default router;
