# HANDOFF
prompt:   2.0.0-alpha.2 — all planned Ps (audit 23 Sep) + owner rulings 1–3
status:   done, ready to deploy
commit:   7ad5db300 on nz-glass (79 commits since last push; all reviewed)
files:    hrms/api/{approvals_list,app_links,calendar,needs_you,request_counts,remote_checkin}.py
          hrms/hr/doctype/remote_checkin_request/remote_checkin_request.py
          frontend/src/views/{Approvals,Profile,More,Requests}.vue
          frontend/src/components/{DaySheet,RequestPanel,RequestBalances,CheckinDecisionSheet}.vue
          frontend/src/components/glass/GModal.vue, theme/glass-components.css, design/tokens.json
verify:   cd frontend && yarn test && node ../design/gates/run.mjs && yarn build
flags:    no migrate/patch needed; banked-OT screens removed (policy), data kept
          OPEN rulings: F-13 tab labels at 200% text; OT form "Replacement Leave" option
next:     deploy nz-glass on Frappe Cloud, then the two rulings
