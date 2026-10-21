GOAL: ship the 12 approved UX review fixes, one commit each.
DONE WHEN: each finding's acceptance check in docs/glass/audit/2026-10-21-ux-review.md passes in the browser on fresh.local:8080.
CHECK: cd frontend && npm test (per-file), plus .claude/tmp/ux/probe.mjs
