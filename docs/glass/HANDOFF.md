# HANDOFF
prompt:   2.0.0-alpha.2 — all planned Ps (audit 23 Sep) + owner rulings 1–3
status:   done, ready to deploy
commit:   b88f52ba5 on nz-glass (all reviewed)
files:    hrms/api/{approvals_list,app_links,calendar,needs_you,request_counts,remote_checkin}.py
          hrms/hr/doctype/remote_checkin_request/remote_checkin_request.py
          frontend/src/views/{Approvals,Profile,More,Requests}.vue
          frontend/src/components/{DaySheet,RequestPanel,RequestBalances,CheckinDecisionSheet}.vue
          frontend/src/components/glass/GModal.vue, theme/glass-components.css, design/tokens.json
verify:   cd frontend && yarn test && node ../design/gates/run.mjs && yarn build
flags:    no migrate/patch needed; banked-OT screens removed (policy), data kept
          F-13 closed (labels fit at 200% after caps removal); Replacement Leave stays (owner)
          follow-ups: zero-balance skeleton collapse; desktop sheet drag; per-list Team tabs
next:     deploy nz-glass on Frappe Cloud
