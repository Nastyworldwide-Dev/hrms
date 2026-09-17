# HANDOFF
prompt:   selfie 403, self-approval chain, faded leave tile
status:   done
commit:   dc06907d5 on nz-glass (b8af8c241 16f6fa473 e3ef2f4de 115516ae2 b3ee126b3)
files:    hrms/api/remote_checkin.py (upload_selfie)
          hrms/api/approval.py + hrms/hr/utils.py (has_approver_above)
          hrms/hr/doctype/{leave_application,expense_claim}/*.py
          hrms/utils/approved_request_guard.py (is_own_request canonical)
          frontend/src/theme/glass-components.css (gloss z-index)
verify:   PYTHONPATH=. python3 -m pytest -q hrms/tests/test_nobody_approves_their_own_request_under_an_approver.py
flags:    Norazlin 2 Sep Half Day vs a 10h punch pair is NOT diagnosed — open
          the Attendance Ownership Check report after deploy; a mirrored
          pre-cutover row with hours is held by design. 3 Sep is a pre-11-Sep
          wrong-log-type punch, 4 Sep is a genuine half day.
next:     Nabil deploys nz-glass; then rule on the three open items in progress.md.
