GOAL: an approver off all day on two half-day leaves is skipped by approval reminders
DONE WHEN: _away_approvers treats an AM half + a PM half on one day as away; a single half is still not away
CHECK: python3 -m pytest -q hrms/tests/test_approval_reminders.py
