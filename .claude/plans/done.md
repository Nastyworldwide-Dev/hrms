GOAL: approved work after the shift is claimable overtime on the day it followed
DONE WHEN: real-DB probe through the approval hook: day 08:55-19:00 + approved 21:00-01:00 -> OT 5.0 h (was 1.0)
CHECK: PYTHONPATH=. python3 -m pytest -q hrms/utils/test_callback_session.py
