GOAL: An employee can withdraw their own approved request and get back exactly
 what the approval granted.
DONE WHEN: the guard allows the owner, finalize elevates for them, the PWA
 offers the button, and a request whose days sit in a submitted salary slip is
 still refused to the employee (HR keeps it).
CHECK: PYTHONPATH=. python3 -m pytest -q
 hrms/tests/test_an_employee_can_withdraw_their_own_request.py
 hrms/tests/test_approved_request_guard.py hrms/api/test_approval.py
