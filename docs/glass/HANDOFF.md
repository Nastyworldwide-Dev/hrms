# HANDOFF
prompt:   the 23 Sep deploy defects, the update-prompt bug, mockup 4 gaps 1-3
status:   done, ready to deploy
commit:   3938741a6 on nz-glass (9 commits since that deploy, all pushed)
files:    design/tokens.json (tab-label 10px, and px rather than rem)
          design/build-tokens.mjs, design/gates/{scale,tabbar-reservation}
          frontend/src/theme/glass-components.css (reservation specificity)
          frontend/src/components/{NowBar,Announcements,RequestBalances}.vue
          frontend/src/views/attendance/Dashboard.vue (four lists removed)
          frontend/src/views/kpi/Dashboard.vue
          hrms/api/{kpi,now,announcements}.py
          hrms/hr/doctype/hr_announcement/hr_announcement.js (HR's reach report)
verify:   cd frontend && yarn test && yarn gates && yarn build
flags:    814/814 tests green, 7 static gates green, ruff clean.
          a11y/visual/coherence still SKIP — they need a served site with
          AUDIT_PW, as they have for six releases. 228 baselines still owed.
          Needs You will still be empty on your account, and that is correct:
          four leave applications are pending on the site and you approve none
          of them. The endpoint is right; the account is not an approver.
          The mockup 4 comparison is docs/glass/audit/2026-09-23-mockup4-gap.md:
          the app follows mockup 4's SHELL, not its CONTENT — six of its blocks
          need data this app does not compute. Gaps 1-3 are now closed.
next:     Deploy. On the phone: the tab bar reads HOME CALENDAR REQUESTS SCORE
          MORE with gaps between them; the "new version" bar stays dismissed
          once you close it; Home's first line states your shift and your
          state; the Calendar is a calendar and nothing sits cut off under the
          bar; Requests splits into "Waiting on someone" and "Finished" with
          four filter chips, and each waiting row says who has it and since
          when; Score names who scores you.
