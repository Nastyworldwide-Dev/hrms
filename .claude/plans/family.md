CLASS: a size read from a hidden page taken as a real position (Ionic hides a tab page while a pushed screen is up; its boxes read 0x0)
frontend/src/components/BaseLayout.vue:64 same-root — the only IntersectionObserver deciding the collapsed title; now via titleCollapsed()
frontend/src/utils/titleCollapse.js:9 same-root — the rule, ignores 0-size roots and targets
frontend/src/components/glass/GAppHeader.vue:127 not-affected — reads the injected state only
