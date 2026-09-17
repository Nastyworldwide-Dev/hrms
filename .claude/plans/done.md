GOAL: Norazlin's 4 Sep could not be paired — the screen ran the action, showed
"The day was rebuilt", and printed Frappe's raw "Attendance ... is already
marked" underneath while nothing changed; and the header read
"[object Object],[object Object]".
DONE WHEN: (1) a day with two live attendance rows refuses every rebuilding
action with one sentence naming the remedy, while remove_duplicate_row still
works on exactly that day; (2) owner_label returns a string or None, never the
classifier's list; (3) the result dialog does not claim a rebuild when the day
came back unchanged.
CHECK: PYTHONPATH=. python3 -m pytest -q hrms/tests/test_fix_day_refuses_a_two_row_day.py hrms/tests/test_fix_day_removes_a_duplicate_row.py hrms/tests/test_fix_day_screen.py && node --test hrms/public/js/fix_day.bundle.test.js
