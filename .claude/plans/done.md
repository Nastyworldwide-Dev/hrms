GOAL: The automatic repair reduces a two-row day to one, without being asked.
DONE WHEN: the endgame has a `duplicates` step between `recovery` and `ot` that
 applies resolve_duplicate_rows, counts what it cancelled for HR's summary, and
 queues one re-mark per day it changed.
CHECK: PYTHONPATH=. python3 -m pytest -q
 hrms/tests/test_endgame_resolves_duplicate_rows.py
