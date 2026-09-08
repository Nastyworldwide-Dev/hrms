# HANDOFF
prompt:   attend-calendar / remote-approval selfie / notification->leave nav+approve
status:   done
commit:   cab04f09d (v16.20.0) on nz-glass
files:    hrms/api/__init__.py
          hrms/api/remote_checkin.py
          frontend/src/views/RemoteApprovals.vue
          frontend/src/router/index.js
          frontend/src/components/FormView.vue
          frontend/src/data/config/requestSummaryFields.js
          hrms/tests/test_attendance_calendar_reads_drafts.py
          frontend/tests/router-shells-distinct-paths.test.mjs
verify:   PYTHONPATH=. python3 -m pytest -q hrms/tests/test_attendance_calendar_reads_drafts.py hrms/tests/test_remote_approvals_carry_the_selfie.py && (cd frontend && node --test tests/router-shells-distinct-paths.test.mjs tests/formview-approver-review.test.mjs)
flags:    calendar cause inferred (Desk row saved, not submitted) — live employee not identifiable via MCP; routing fix from Ionic source, not browser-verified (no fresh.local login)
next:     FC deploy of v16.20.0 is pending on Frappe Cloud; then approver re-tests notification -> Back and Approve or reject on a live request
