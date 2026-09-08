# HANDOFF
prompt:   team-calendar (Team tab: month picker + stat strip replace day arrows)
status:   done
commit:   see `git log -1 --format=%h v16.22.0` (v16.22.0) on nz-glass
files:    frontend/src/views/team/TeamDashboard.vue
          frontend/src/utils/team.js
          frontend/src/theme/glass-components.css
          frontend/tests/team-calendar-days.test.mjs
verify:   cd frontend && node --experimental-test-module-mocks --test tests/team-calendar-days.test.mjs && yarn build
flags:    grid marks selected day + today only (no per-day team status tint); "10AM - 7PM" attendance gap for HR-EMP-00102 on 07-09 diagnosed, not fixed (needs HR-level read of her check-ins)
next:     FC deploy of v16.22.0 on verifica-live; Helpdesk native front end awaits plan approval (.claude/plans/current-plan.md)
