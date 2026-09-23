# HANDOFF
prompt:   the 23 September deploy — every defect in the owner's screenshots
status:   done, ready to deploy
commit:   4fa619563 on nz-glass (5 commits since that deploy, all pushed)
files:    design/tokens.json (tab-label 10px, and px rather than rem)
          design/build-tokens.mjs, design/gates/{scale,tabbar-reservation}
          frontend/src/theme/glass-components.css (reservation specificity)
          frontend/src/components/{NowBar,Announcements,RequestBalances}.vue
          frontend/src/views/attendance/Dashboard.vue (four lists removed)
          frontend/src/views/kpi/Dashboard.vue
          hrms/api/{kpi,now,announcements}.py
          hrms/hr/doctype/hr_announcement/hr_announcement.js (HR's reach report)
verify:   cd frontend && yarn test && yarn gates && yarn build
flags:    789/789 tests green, 7 static gates green, ruff clean.
          a11y/visual/coherence still SKIP — they need a served site with
          AUDIT_PW, as they have for six releases. 228 baselines still owed.
          Needs You will still be empty on your account, and that is correct:
          four leave applications are pending on the site and you approve none
          of them. The endpoint is right; the account is not an approver.
next:     Deploy. On the phone: the tab bar reads HOME CALENDAR REQUESTS SCORE
          MORE with gaps between them; Home's first line states your shift and
          your state; the Calendar is a calendar and nothing sits cut off under
          the bar; Requests shows four balances that say "of N"; Score names
          who scores you.
