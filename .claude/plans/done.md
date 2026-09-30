GOAL: a record calendar returned as a dict carries its real start date, so a split date range never adds days to None.
DONE WHEN: _record_calendar as_dict returns the Holiday List's from_date; test red before, green after.
CHECK: PYTHONPATH=. python3 -m pytest -q hrms/tests/test_holiday_list.py
