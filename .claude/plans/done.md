GOAL: a sent request shows its story — sent, then each decision with who and when, and the reason when not approved
DONE WHEN: bench: owner and approver read "Sent by W0 employee" then "Not approved by W0 approver · reason"; three strangers refused; screen shows the History group in light and dark
CHECK: PYTHONPATH=.:hrms/tests python3 -m pytest -q hrms/api/test_request_history.py && cd frontend && node --test src/components/__tests__/request-timeline.test.js
