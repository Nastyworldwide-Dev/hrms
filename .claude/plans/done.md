GOAL: The payroll check behind a withdrawal reads the request's real period.
DONE WHEN: every entry in REQUEST_PERIOD_FIELDS is a real Date field on its
 doctype (asserted from the JSON), a doctype absent from the map refuses the
 employee, and the three refusals say three different things.
CHECK: PYTHONPATH=. python3 -m pytest -q
 hrms/tests/test_an_employee_can_withdraw_their_own_request.py
