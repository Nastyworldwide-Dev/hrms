GOAL: HR sees every day the midnight bug damaged, to fix with Fix a day
DONE WHEN: report exists after migrate and runs; find_missed tests: IN->IN 03:00 listed; OUT, after-06:00, other employee, rejected not listed
CHECK: PYTHONPATH=.:hrms/tests python3 -m pytest -q hrms/hr/report/missed_checkouts_after_midnight/
