# HANDOFF
prompt:   5.6 (batch 4 — KPI + Issues)
status:   done
commit:   bf4ff8559 on nz-glass
files:    frontend/src/views/kpi/Dashboard.vue
          frontend/src/views/issues/{IssueList,HRIssueBoard}.vue
          frontend/src/views/ot/ReplacementLeave.vue
          design/gates/surfaces.mjs (multi-line v-for detection)
          docs/glass/spec/…v1.1.md (§12 Issues split, Issue board, KPI)
verify:   cd frontend && yarn gates && yarn build
flags:    COUNTS — IssuesTab 2/6 (content 1 + tab bar; the two branches are v-if/v-else so
          the MAX applies), HRIssueBoard 1/6, IssueList 1/6, kpi/Dashboard 1/6,
          ReplacementLeave 0/6. Nothing near the limit
          COUNTER BUG FOUND AND FIXED: v-for was only detected on the same line as the tag.
          IssueList's GIssueCard spans several lines, so N cards counted as 1. With the fix
          the gate flagged it — CORRECTLY: 8 open tickets would exceed the budget alone
          ISSUE LIST NOW FLATTENS to one GListPanel. GIssueCard stays for the bounded
          dashboard context §15.2 actually counted (it assumed two cards)
          ISSUES IS TWO SCREENS: IssuesTab routes HR → board, staff → own list. §12 had one
          anatomy for both. Both now in the table; the HR board's anatomy written from scratch
          KPI HAS NO GOALS PANEL and no verdict line — §12 lists both. goal_completion is a
          KRA row field. Nothing to style; recorded, not invented
          HRIssueBoard is the ONE screen with a real text search → the one place GSearchBar
          belongs, closing the 5.5 note
next:     batches 6-9 (SOP, Team, settings, auth) — SOP needs the unbuilt PDF viewer
