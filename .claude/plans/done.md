GOAL: a Shift Supervisor rosters themselves and whoever reports to them, whatever their company lock; strangers stay refused.
DONE WHEN: rostered_employees is the one list for the write fence and the shift row scope; insert_shift saves for self and a cross-company report; stranger refused; tests red before, green after; fresh.local 5-case matrix.
CHECK: PYTHONPATH=. python3 hrms/tests/test_supervisor_rosters_self_and_line.py && PYTHONPATH=. python3 hrms/tests/test_shift_supervisor_rosters_own_team.py
