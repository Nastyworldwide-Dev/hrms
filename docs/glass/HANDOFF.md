# HANDOFF
prompt:   approver chain — "it persist again" + "close it"
status:   done
commit:   5134f4856 on nz-glass
files:    hrms/hr/utils.py
          hrms/api/__init__.py
          hrms/hr/doctype/shift_request/shift_request.py
          hrms/tests/test_approver_chain_follows_each_employee.py
          hrms/tests/test_shift_requests_route_by_the_same_chain.py
          hrms/tests/test_nobody_approves_their_own_request_under_an_approver.py
          hrms/tests/_frappe_stub.py
verify:   PYTHONPATH=. python3 -m pytest -q hrms/tests/test_approver_chain_follows_each_employee.py hrms/tests/test_shift_requests_route_by_the_same_chain.py
flags:    Department Approver removed as a routing source for all four request types (owner: "no, dont" + "close it"). get_department_approvers deleted. Two open items in .claude/plans/ticket-approver-chain-consolidation.md: duplicated walker logic, and the company fence that only applies to fenced callers.
next:     deploy on Frappe Cloud, then confirm a grand-manager can decide a lapsed On Duty request on the live site.
