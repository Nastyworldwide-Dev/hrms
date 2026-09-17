GOAL: A stutter of taps cannot write a session.
DONE WHEN: a punch landing within BURST_WINDOW of the employee's previous punch
 is stored, skip-stamped and commented — never refused — and a real gap, a
 mirrored row and a rejected punch never start a burst.
CHECK: PYTHONPATH=. python3 -m pytest -q hrms/tests/test_a_tap_burst_is_one_tap.py
