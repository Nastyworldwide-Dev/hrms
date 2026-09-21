# HANDOFF
prompt:   release-3 (requests tell the truth)
status:   done
commit:   306394c5f on nz-glass (pushed)
files:    frontend/src/{socket.js,composables/realtime.js,data/requestLists.js,utils/siteTime.js,utils/requestStatus.js}
          frontend/src/components/{RequestPanel,RequestActionSheet,FormView,glass/GStatusChip}.vue + six *Item.vue
          hrms/hr/doctype/{leave_application,shift_request,expense_claim,ot_request,replacement_leave_claim}/*.py
          hrms/hr/utils.py · hrms/mixins/pwa_notifications.py · hrms/api/approval.py · hrms/patches/v16_0/track_changes_on_leave_and_expense.py
verify:   cd frontend && npm test; PYTHONPATH=.:hrms/tests python3 -m pytest -q hrms/tests/test_a_decision_is_always_recordable.py
flags:    migrate + bundle build + worker restart. Ruling needed: an OT/RL cancel is refused when its leave was already taken (HR must cancel the leave first). Not done: RL grant dated by worked day; Leave-cancel ledger reverse; expense_date in the PWA; reminders (4 answers pending).
next:     owner deploys R3 after R2; then reminders once the four answers are in (docs/glass/release-3-notes.md).
