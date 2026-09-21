# HANDOFF
prompt:   Thread F — unify request status across the request family
status:   partial
commit:   aea8da075 on nz-glass
files:    frontend/src/utils/requestStatus.js
          frontend/src/utils/__tests__/requestStatus.test.js
          frontend/src/views/RemoteApprovals.vue
          .claude/plans/current-plan.md
          .claude/plans/family.md
          .claude/plans/ticket-waiting-word-in-filters.md
          .claude/plans/progress.md
verify:   cd frontend && node --experimental-test-module-mocks --test src/utils/__tests__/*.test.js src/components/__tests__/*.test.js
flags:    slice 5 (RequestPolicy + date windows) needs the owner's backdating
          ruling; Shift Request and Expense Claim have no window at all today.
          Leave/shift list filters still offer the stored word (ticket filed).
next:     deploy ecc3b8d7b+aea8da075 on Frappe Cloud, then slice 5.
