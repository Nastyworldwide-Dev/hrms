# HANDOFF
prompt:   audit + late-checkout fix
status:   done
commit:   776ee69ec on nz-glass
files:    hrms/api/remote_checkin.py
          hrms/overrides/remote_checkin_request_hooks.py
          hrms/hr/doctype/shift_type/shift_type.py
          hrms/api/test_remote_checkin.py
          hrms/tests/test_remote_checkin_request_hooks.py
          hrms/tests/_frappe_stub.py + conftest.py
          docs/glass/nadi-audit-2026-09-07.md
verify:   python3 -m pytest -q hrms/api/test_remote_checkin.py hrms/tests/test_remote_checkin_request_hooks.py hrms/tests/test_checkin_timezone.py
flags:    attendance re-mark leaves a hand-marked Attendance alone; bench doctype suites fail on leaked fixtures (not on this change)
next:     Nabil deploys; then audit fix plan row 1 (launcher child icon roles) and row 2 (payroll report timestamps + patch)
