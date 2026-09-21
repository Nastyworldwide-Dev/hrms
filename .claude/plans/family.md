CLASS: `Department Approver` was still a routing source for ONE doctype. A name
ticked on a department admitted an approver that no employee record routes to —
and for the selector, every approver ticked on any ANCESTOR department too. Owner
ruling 21 Sep 2026 ("no, dont"), extended to Shift Request the same day ("close
it"). Second defect in the same place: the selector and the save fence read two
DIFFERENT lists (ancestor walk vs. the immediate department's table), so a pick
from the dropdown could be refused on save.

Instance test: hrms/tests/test_shift_requests_route_by_the_same_chain.py
Invariant test: same file, TestTheShiftValidatorAcceptsTheSameList::
  test_everything_offered_is_accepted — every option the selector offers must
  pass the fence, for every employee in the fixture.

Call sites of get_shift_request_approvers / ShiftRequest.validate_approver /
get_department_approvers:

hrms/api/__init__.py:980 get_shift_request_approvers same-root — now builds from
  _approver_options, the same helper the leave and expense selectors use.
hrms/hr/doctype/shift_request/shift_request.py:106 validate_approver same-root —
  now reads get_designated_approvers, the list the selector offers.
hrms/hr/doctype/shift_request/shift_request.py:34 ShiftRequest.validate
  same-root — the only caller of validate_approver; unchanged, calls the fixed
  fence.
hrms/api/__init__.py get_department_approvers same-root — the ancestor walk had
  no caller left after the two above; deleted rather than kept as a trap.
frontend/src/views/attendance/ShiftRequestForm.vue:71 not-affected — the
  response contract is unchanged (a list of {name, full_name}); the form still
  defaults to data[0], which is still the immediate superior.

Not affected:
hrms/tests/test_self_service_department_reads.py — an AST test that
  get_shift_request_approvers demands no Desk permission. Still true: the new
  body has no has_permission call. Green.
hrms/tests/test_leave_draft_creation.py:139 — asserted an ancestor-department
  approver is not offered for LEAVE. Still true; its docstring referred to the
  deleted function and was corrected.
