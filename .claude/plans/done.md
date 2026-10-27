GOAL: an Event opened from the calendar off the board shows no Confirm (owner, 27 Oct 2026).
DONE WHEN: get_announcement returns live; Detail hides tick + Confirm when live is false.
CHECK: pytest hrms/api/test_calendar_events_by_date.py; node --test frontend/src/components/__tests__/must-read-tickbox.test.js
