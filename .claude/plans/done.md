GOAL: an employee can withdraw their own draft even when a deleted request's cancelled rows still carry its re-used name
DONE WHEN: bench: approve -> cancel -> delete -> new draft reuses the name with a cancelled Attendance on it -> withdraw succeeds; a live link still refuses
CHECK: PYTHONPATH=.:hrms/tests python3 -m pytest -q hrms/tests/test_withdraw_reused_name.py
