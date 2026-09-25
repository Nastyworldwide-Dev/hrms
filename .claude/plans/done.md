GOAL: half-day leave says AM or PM, and the person is not marked late (AM) or early (PM) for the half they were off
DONE WHEN: real-DB probe: AM half approved on a day marked late at mid+5 min -> late 0; at mid+20 -> late 1; new half day without session refused; approver reads "Half day · AM"
CHECK: PYTHONPATH=.:hrms/tests python3 -m pytest -q hrms/utils/test_half_day_session.py hrms/tests/test_half_day_session_late_early.py
