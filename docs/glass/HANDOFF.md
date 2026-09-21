# HANDOFF
prompt:   approver message clarity
status:   done
commit:   ab74a7904 on nz-glass
files:    hrms/hr/utils.py
          hrms/hr/doctype/shift_request/shift_request.py
          hrms/tests/test_no_approver_configured_says_so.py
          .claude/plans/family.md
verify:   PYTHONPATH=. python3 -m pytest -q hrms/tests/test_no_approver_configured_says_so.py
flags:    none
next:     deploy on Frappe Cloud, then file a request as an employee with no approver and confirm the message names HR
