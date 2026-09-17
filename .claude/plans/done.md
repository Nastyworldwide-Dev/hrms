GOAL: The burst comment is written in the type the skip-reason readers query.
DONE WHEN: the burst path calls add_comment("Comment", ...), and a test reads
 the type from the writer AND from the audit's query and fails if they differ.
CHECK: PYTHONPATH=. python3 -m pytest -q hrms/tests/test_a_tap_burst_is_one_tap.py
