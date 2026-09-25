# HANDOFF
prompt:   alpha.8 r3 — zoom off, scroll, jumps
status:   done
commit:   b152fe9c8 on nz-glass
files:    frontend/index.html, src/utils/blockZoom.js, src/components/ListView.vue
          src/theme/glass-components.css, NeedsYou.vue, Approvals.vue, RequestBalances.vue
          e2e/scroll-and-shift-audit.mjs, e2e/sheet-shift-audit.mjs
verify:   cd frontend && node e2e/scroll-and-shift-audit.mjs && node e2e/sheet-shift-audit.mjs
flags:    empty queues are now a row in a group (D1, D5); Leave left always shows ("None allocated yet")
next:     alpha.9 D10/D11 (name not ID, no Company on own requests), then D2–D9 into groups
