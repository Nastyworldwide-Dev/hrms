# HANDOFF
prompt:   Employee Status -> Active/Resigned/Terminated/Deceased/Suspended (10 Nov 2026)
status:   done
commit:   c9b0e8454 (alpha.87, tag v2.0.0-alpha.87) on nz-glass
files:    hrms/utils/employee_status.py (new)
hrms/patches/v16_0/employee_status_options.py (new)
hrms/overrides/employee_master.py, hrms/sync/runner.py
hrms/hr/offboarding.py, salary_slip.py, hr/utils.py, 4 report .js
verify:   after deploy + migrate: Employee Status dropdown shows the 5 options; no Employee is Left/Inactive
flags:    no bench site, site tests not run; owner: Terminated/Deceased label-only, Inactive guards left; former Inactive staff with no relieving date may enter payroll until HR fills it
next:     deploy alpha.87 on Frappe Cloud WITH migrate; HR fills relieving dates before next payroll
