CLASS: one message for two different situations. Both approver fences threw the
same text whether the employee picked the wrong approver (they can fix it from
the dropdown) or had NO approver configured at all (only HR can fix it, in
Desk). "Please select your reporting manager" pointed at an empty dropdown.
Owner ruling 21 Sep 2026: "make it clear and not confusing", on the standing
project rule that the system self-identifies — we never ask an employee or HR to
run a URL or a console step to find out what is wrong.

Instance test: hrms/tests/test_no_approver_configured_says_so.py
Invariant test: same file, TestAWrongPickStillSaysWrongPick — a non-empty list
  keeps the original wording, so the new branch cannot swallow the old one.

Call sites of validate_staff_approver / no_approver_message:

hrms/hr/utils.py:1471 validate_staff_approver same-root — the throw now routes
  through no_approver_message.
hrms/hr/doctype/leave_application/leave_application.py:123 same-root — the
  wrapper that calls the fixed fence; no change needed here, the message follows.
hrms/hr/doctype/leave_application/leave_application.py:106 same-root — validate()
  calling that wrapper; the new message reaches a leave filing through it.
hrms/hr/doctype/expense_claim/expense_claim.py:186 same-root — the same wrapper.
hrms/hr/doctype/expense_claim/expense_claim.py:65 same-root — validate() calling
  it; the new message reaches an expense claim through it.
hrms/hr/doctype/shift_request/shift_request.py:130 same-root — has its own throw
  (its list comes from the same resolver but the wording differed); now shares
  the empty-list branch and keeps its own wrong-pick wording.
hrms/overrides/approval_row_scope.py:105 not-affected — a comment naming the
  fence, not a call.
hrms/api/team.py:49, hrms/api/approval.py:56, hrms/api/__init__.py:1237,1276
  not-affected — comments and docstrings naming the fence, not calls.

Not affected:
Attendance Request, OT Request, Replacement Leave Claim, Compensatory Leave
  Claim — they do not call validate_staff_approver; their approver is resolved
  at decision time by hrms.api.approval, which has its own messages. Out of
  scope for this commit and not part of the reported confusion.
