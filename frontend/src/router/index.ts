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
  ],
});

export default router;
