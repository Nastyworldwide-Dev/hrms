CLASS: approval routing asked the wrong question in two opposite directions —
a `Department Approver` row admitted a whole department that no employee record
routes to (too wide), while the per-employee walk stopped after one rung, so the
escalation an employee actually has when their approver forgets was not an
approver at all (too narrow). Owner ruling 21 Sep 2026: bottom-up, per employee,
until nobody is above; no department blanket; no hardcoded depth.

Instance test: hrms/tests/test_approver_chain_follows_each_employee.py
Invariant test: same file, TestTheInverseAgreesWithTheChain::
  test_the_two_directions_never_disagree — whoever may approve for an employee
  must also be able to see them, for every employee in the fixture.

Call sites of get_designated_approvers / get_employees_routed_to:

hrms/api/__init__.py:356 _may_read_employee — same-root. Read fence now admits
  the whole chain and no department approver; that is the fix.
hrms/api/__init__.py:1305 _approver_options — same-root. Options now come from
  the chain.
hrms/api/__init__.py:1257 get_leave_approval_details — same-root. Prefilled from
  Department Approver row 1, a value the save would now always reject; replaced
  by _default_approver.
hrms/api/__init__.py:1521 get_expense_approval_details — same-root, same defect.
hrms/api/approval.py:128 same-root — _is_routed_approver. A named superior one
  or more rungs up can now decide; a department approver no longer can.
hrms/hr/utils.py:1076 has_approver_above — same-root. Self-approval refusal now
  keys on the chain; test amended
  (test_a_department_approver_is_not_somebody_above_them).
hrms/hr/utils.py:1459 validate_staff_approver — same-root. Save fence reads the
  same list the selector now offers.
hrms/mixins/pwa_notifications.py:144 same-root — _get_ot_approver. Still takes
  the first entry; order is still bottom-up, so the immediate superior is still
  the recipient.
hrms/overrides/employee_owned_row_scope.py:233 same-root — list scope narrows
  (department blanket gone) and widens (chain above). Suites green.
hrms/overrides/employee_owned_row_scope.py:284 same-root — the row read of the
  same list.
hrms/overrides/ot_row_scope.py:52 same-root — same two effects, same list.
hrms/overrides/ot_row_scope.py:90 same-root — the row read of the same list.

Not affected:
hrms/hr/doctype/shift_request/shift_request.py validate_approver and
  hrms/api/__init__.py get_shift_request_approvers read `get_department_approvers`
  (the ancestor walk), not this pair — a separate source, out of scope this
  commit, already on the open list.
Test files listed by the scan (test_*.py) — assertions, not call sites.
