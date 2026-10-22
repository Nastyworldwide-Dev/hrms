GOAL: Employee cost split is per Year/Month and labelled Cost Tag/Center.
DONE WHEN: validate checks 100% per month; report picks latest month <= slip month; old rows stamped by patch.
CHECK: PYTHONPATH=.:hrms/tests python3 -m pytest -q hrms/tests/test_employee_interco_allocation.py hrms/payroll/report/intercompany_salary_cost_allocation/test_intercompany_salary_cost_allocation.py hrms/tests/test_stamp_cost_allocation_month_patch.py
