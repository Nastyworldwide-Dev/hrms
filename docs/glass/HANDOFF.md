# HANDOFF
prompt:   Employee Status -> Active/Resigned/Terminated/Deceased/Suspended (10 Nov 2026)
status:   partial
commit:   eda1ace50 on nz-glass (no version bump/tag yet)
files:    hrms/utils/employee_status.py (new)
hrms/patches/v16_0/employee_status_options.py (new)
hrms/overrides/employee_master.py
hrms/sync/runner.py, hrms/hr/offboarding.py, salary_slip.py, hr/utils.py
hrms/public/js/erpnext/employee_list.js (new), 4 report .js
verify:   python3 -m pytest -q hrms/utils/test_employee_status.py hrms/overrides/test_employee_status_rules.py hrms/patches/v16_0/test_employee_status_options.py hrms/tests/test_leaver_status_everywhere.py; deploy needs bench migrate
flags:    no bench site, site tests not run; Inactive guards now never fire (owner Q2); Terminated/Deceased label-only (owner Q1)
next:     owner answers Q1/Q2, then version bump + Frappe Cloud deploy + migrate
