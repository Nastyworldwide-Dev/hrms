GOAL: a supervisor's shift is always filed under the employee's own company, never one the browser sent.
DONE WHEN: insert_shift reads company from Employee for the admitted line; test red before, green after.
CHECK: PYTHONPATH=. python3 hrms/tests/test_supervisor_rosters_self_and_line.py
