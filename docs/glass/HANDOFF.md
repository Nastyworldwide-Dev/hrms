# HANDOFF
prompt:   alpha.38 "Money and Waiting" (owner rulings R1-R5 + SOPs + leftovers)
status:   done (K1 pipeline consolidation not started: needs write access to /opt/keel)
commit:   b8137433b on nz-glass (tag v2.0.0-alpha.38, GitHub Release created)
files:    hrms/hr/doctype/expense_claim/expense_claim.py (duplicate claims)
          hrms/utils/approval_reminders.py (approver away)
          hrms/utils/cancel_notice.py + hrms/hooks.py (cancel notices)
          frontend/src/views/sop/SopFormSheet.vue (SOP editor)
          frontend/src/utils/loudRequest.js (offline, refusal wording)
          frontend/src/components/FormView.vue, ResourceError.vue, MustReadNotice.vue
          docs/glass/audit/2026-10-06-*.md (supervisor Desk, approver reports)
verify:   on the live site after the update: run migrate (refreshes the hook cache for cancel notices); file the same claim twice -> refused
flags:    frontend/tests is run by no gate (went red twice unseen); humanless-pipeline commits stay local by owner ruling
next:     owner puts alpha.35-38 live; then K1 (one pipeline copy, gate runs frontend/tests)
