# HANDOFF
prompt:   astra-6-review
status:   done
commit:   cf513efad on nz-glass
files:    hrms/sync/preflight.py
          hrms/sync/parity.py
          hrms/hr/doctype/hrms_erp_instance/hrms_erp_instance.js
          frontend/src/views/expense_claim/Form.vue
          design/gates/verdict.mjs + run.mjs
          .github/workflows/linters.yml
          frontend/src (eslint --fix, 21 files)
verify:   PYTHONPATH=. python3 hrms/tests/test_sync_endpoints_are_fenced.py && PYTHONPATH=. python3 hrms/tests/test_sync_parity.py && (cd frontend && yarn lint && yarn test)
flags:    #3 audit still count-only by design (deeper per-record parity deferred); test_ot_request.py case is bench-only (not run here)
next:     push; Nabil deploys; then seed 5 Expense Claim Types w/ per-company accounts on Verifica
