# HANDOFF
prompt:   4.4 (phase 4 complete — shell done)
status:   done
commit:   3a7b1df5c on nz-glass
files:    design/gates/usage.mjs (views strict)
          design/gates/surfaces.mjs (rebuilt: counts what renders)
          design/gates/run.mjs (summary line)
          docs/glass/phase5-plan.md
verify:   cd frontend && yarn gates
flags:    SURFACE COUNTS: 9 tab destinations at 1/6 (chrome only), More at 2/6, everything
          else 0. NOTHING exceeds 6 — content counts are 0 because phase 5 has not composed
          the components yet, which is the expected state, not a passing grade
          §15.2 FLATTENING now ASSERTED not remembered: GBalanceGrid 1 (was 4), GStatPanel 1
          (was 3), GListPanel 1, and four GIssueCards still 4. Always fails if broken
          surfaces gate left REPORT-ONLY: it has nothing to measure until screens compose
          components. Flip to --strict when batch 1 lands, not before
          counter bug fixed: the router parse sliced past TabbedView's children and gave the
          tab bar to Login/ForgotPassword/ChangePassword/AppSettings
          28 of 38 screens have NO §12 anatomy. HRIssueBoard and expense_claim/Dashboard
          need a ruling before their batch; the rest genuinely follow settled patterns
          5 files still use frappe-ui Dialog and must swap to GModal — FormView.vue is the
          one that matters, it backs all 7 form screens
next:     phase 5 batch 1 (Home), then flip surfaces to --strict
