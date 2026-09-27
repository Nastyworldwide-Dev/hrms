GOAL: notifications read at a glance — same person + kind fold into one row with a count; opening a fold marks it read
DONE WHEN: live approver feed shows "W0 employee asked for time off · 11"; opening it lists the 11 indented on the fold's text and the unread count drops (78 -> 67); only the caller's rows can be marked
CHECK: PYTHONPATH=.:hrms/tests python3 -m pytest -q hrms/tests/test_notification_mark_read.py && cd frontend && node --test src/utils/__tests__/foldNotifications.test.js
