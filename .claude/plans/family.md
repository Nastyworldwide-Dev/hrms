CLASS: a new component's CSS class reuses a name an existing Glass component already owns (.g-ring = GProgressRing)
frontend/src/components/RequestBalances.vue same-root — renamed to .g-leave-ring*; test asserts one .g-ring rule
frontend/src/components/glass/GProgressRing.vue same-root — its .g-ring rule was overridden by the new block (KPI dial); restored by the rename
frontend/src/views/kpi/Dashboard.vue not-affected — uses GProgressRing, which is restored
frontend/src/views/kpi/KpiDetail.vue not-affected — uses GProgressRing, which is restored
frontend/src/components/glass/GScorePanel.vue not-affected — uses GProgressRing, which is restored
frontend/src/utils/requestsPage.js same-root — ringArcs: carry-forward cut the taken arc; circle is now max(total, left+taken)
