# HANDOFF
prompt:   claims in the PWA (expense / OT / replacement leave) + GL accounts from the ERP
status:   done (reviewed, Important fixed in 9b6e21803); pushed; deploy pending
commit:   9b6e21803 on nz-glass
files:    hrms/sync/account_shells.py (+ Pull → GL Accounts button, grouped instance buttons)
          hrms/api/__init__.py (types offered, payable prefill, status on OT lists, RL discovery)
          hrms/hr/doctype/expense_claim/expense_claim.py (payable default)
          hrms/hr/doctype/ot_request/ot_request.py, replacement_leave_claim.py, hrms/mixins/pwa_notifications.py
          frontend/src/components/{FormView,ListView,OTRequestItem,ReplacementLeaveClaimItem}.vue, utils/requestStatus.js
          docs/glass/audit/2026-09-09-claims-audit.md
verify:   PYTHONPATH=. python3 hrms/tests/test_request_outcome_visible.py; cd frontend && node --experimental-test-module-mocks --test tests/*.test.mjs
flags:    six policy rulings in the audit §3 (RL Claim retire, rejected date release, RL cap, Overtime Slip, backdating, rejection reason)
next:     read review; push; Nabil deploys → Pull → GL Accounts → configure Expense Claim Types → staff test one claim of each kind
