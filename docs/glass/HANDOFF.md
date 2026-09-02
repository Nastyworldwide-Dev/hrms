# HANDOFF
prompt:   polish sweep — liquid-glass audit + frontend/backend contract
status:   partial
commit:   01a7cc71d on nz-glass (7 commits from 233366bf6)
files:    frontend/src/theme/glass-components.css + design/tokens.json (glass.css)
          frontend/src/components/glass/{GBanner,GBalanceGrid,GProviderButton}.vue + GBanner.test.js
          frontend/src/components/{CheckInPanel,PendingApprovalsBanner}.vue
          frontend/src/views/team/TeamRoster.vue
          design/gates/lint.mjs + lint-baseline.json + token-collapse-baseline.json
verify:   cd frontend && yarn tokens && yarn build && node --test "src/**/*.test.js" && node ../design/gates/run.mjs
flags:    a11y/visual/coherence gates unrun (need served worktree + AUDIT_PW; bench serves main, /hrms 404s).
          backend batch dropped: attachment_content is LIVE (sop.py:180 builds its URL — agent was wrong);
          report_half_transitioned + get_company_currencies-guard = low value / real risk, left for a decision.
next:     serve this worktree to run the 3 rendered gates; decide check-in success pulse (spec'd, unbuilt).
