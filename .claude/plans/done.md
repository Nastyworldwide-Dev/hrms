GOAL: offline launch works from the worker's own cache, not by luck of the browser cache; old installs move cleanly
DONE WHEN: precache holds /assets/hrms/frontend/* as real JS; offline relaunch with the HTTP cache cleared loads Today; old worker retired; push re-subscribed once
CHECK: cd frontend && node --test src/__tests__/sw.test.js
