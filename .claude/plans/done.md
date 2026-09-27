GOAL: Score's "no review yet" is a plain grouped row, not an info banner with a lime bar.
DONE WHEN: KpiDashboard mine-branch uses GListPanel + GListRow; no GBanner there.
CHECK: node --test frontend/src/views/__tests__/score-empty-path.test.js; WebKit Score screenshot
