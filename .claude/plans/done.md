GOAL: no band of chrome above a page: the bar is its 44 pt row and the large title follows it directly (Apple navigation bar).
DONE WHEN: .g-header has no vertical padding, min-height 44; device journey J2 = 0 on every tab stop.
CHECK: node --test frontend/src/components/glass/__tests__/ios-nav-bar.test.js; device-journey-audit GATE_COUNT 0 (was 29 J2)
