# HANDOFF
prompt:   alpha.5 — whole app, one design, no residue ("go till finish")
status:   done (deploy only)
commit:   v2.0.0-alpha.5 (07bb1249d) on nz-glass
files:    frontend/src/components/glass/GModal.vue, ShellHeader.vue, FormField.vue
          frontend/src/views/Notifications.vue, helpdesk/HelpdeskHub.vue, HelpSplitList.vue
          frontend/src/theme/glass-components.css (glass on chrome only)
          hrms/utils/worked_days.py + hrms/api/{calendar,requests_summary,home}.py
          hrms/www/hrms.py (site time zone in the PWA boot)
          docs/glass/CHANGELOG.md, docs/glass/plan/alpha5-review.html
verify:   cd frontend && yarn test ; after deploy: open Notifications (times right), Calendar (today green)
flags:    No patch, no schema change. Taken as recommended (owner delegated): H1 keep Home, H4 keep mark+date, C4 fills + Fix/OT dots, H3 Approvals not in More. Half-height sheets dropped (focus-trap). Tickets: FormView menu, worked-days table, approval toast, non-English issue text.
next:     deploy 2.0.0-alpha.5
