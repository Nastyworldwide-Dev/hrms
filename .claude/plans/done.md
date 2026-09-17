GOAL: A burst tap that was really a short session reaches HR's list.
DONE WHEN: the burst comment carries the Attendance Day Audit's own SKIP_PREFIX
 and its reason is in REPAIRABLE_SKIP_REASONS, so the audit lists it with
 "unskip"; and a row dict with no docstatus is no longer read as a draft.
CHECK: PYTHONPATH=. python3 -m pytest -q hrms/tests/test_a_tap_burst_is_one_tap.py
