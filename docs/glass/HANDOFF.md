# HANDOFF
prompt:   alpha.14 — whole-app pass, roster facts, security, first paint
status:   done
commit:   12e4084f3 on nz-glass (tag v2.0.0-alpha.14, GitHub Release published)
files:    frontend/e2e/device-journey-audit.mjs (installed-iPhone gate)
          frontend/src/components/CheckinSheet.vue, glass/GAttachmentRow.vue
          hrms/hr/report/roster_patterns/ (HR Desk report + link patch)
          hrms/tests/test_desk_writes_are_post_only.py
          docs/glass/plan/NADI_2.0.0-alpha.14_PLAN.md (shipped table)
          mockups/mockup-nadi-a14-{balance-strip,team-calendar}.html
verify:   deploy; Desk > Shift & Attendance > Roster Patterns; You shows "Nadi 2.0.0-alpha.14 · Clear Screens and Safer Sign-in"
flags:    roster design waits on live Roster Patterns numbers; balance strip + Team calendar wait on mockup sign-off; FCP 5.28 s (target 5 s not met); helpdesk.get_ticket fence unverified (no Helpdesk on bench)
next:     owner deploys, signs off the two mockups, shares Roster Patterns numbers
