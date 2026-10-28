# HANDOFF
prompt:   Cost Tag/Center lists Cost Centers, not Territories (owner, 28 Oct 2026)
status:   done
commit:   329b0ed83 on nz-glass (feature ee3c86df2)
files:    hrms/hr/doctype/employee_interco_allocation/employee_interco_allocation.json
hrms/patches/v16_0/link_cost_allocation_cost_center.py
hrms/overrides/employee_interco_allocation.py
hrms/payroll/report/intercompany_salary_cost_allocation/intercompany_salary_cost_allocation.py
hrms/public/js/erpnext/employee.js
hrms/tests/test_link_cost_allocation_cost_center_patch.py
verify:   deploy + bench migrate; Employee -> Cost Tag/Center Allocation -> dropdown lists Main, CEOF, PFME...
flags:    not run on a bench (no local site has hrms); unmatched old rows keep Territory by design
next:     owner checks on staging; org chart resumes from ~/org-chart-paused/README.md
