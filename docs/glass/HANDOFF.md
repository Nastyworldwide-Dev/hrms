# HANDOFF
prompt:   remote check-in approver routing
status:   done
commit:   353ceb7d6 on nz-glass
files:    hrms/overrides/remote_checkin_request_hooks.py
          hrms/api/approval.py
          hrms/api/remote_checkin.py
          hrms/overrides/employee_checkin_after_insert.py
          hrms/tests/test_remote_checkin_routes_up_the_chain.py
          hrms/tests/test_remote_checkin_request.py
          hrms/tests/test_company_api_scope.py
          hrms/overrides/test_remote_checkin_request_hooks.py
verify:   PYTHONPATH=. python3 -m pytest -q hrms/tests/test_remote_checkin_routes_up_the_chain.py
flags:    team.py's Department Approver tab gate left as-is (display only, ticketed)
next:     deploy on Frappe Cloud, then have a senior approver decide a remote punch whose named approver did not act
