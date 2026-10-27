GOAL: the calendar draws a half-day leave as a working day, as Home, reminders and Team do
DONE WHEN: _leave_days returns whole days off only (an AM + PM pair counts); half days are not leave days on the grid
CHECK: python3 -m pytest -q hrms/api/test_calendar_kinds.py
