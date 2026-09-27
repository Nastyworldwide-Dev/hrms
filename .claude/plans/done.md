GOAL: coming Back to a tab shows one title, never the bar's small title and the large one together.
DONE WHEN: a hidden tab page keeps its title state; device journey J1 = 0 on all five tabs.
CHECK: node --test frontend/src/utils/__tests__/titleCollapse.test.js; device-journey-audit J1 0 (was 5)
