# HANDOFF
prompt:   Manpower Request: hide from Administrator; sender, approver and HR only (owner, 29 Oct 2026)
status:   done
commit:   alpha.76 on nz-glass (791270ac4, 11d74bd1b, print fix)
files:    hrms/overrides/employee_owned_row_scope.py
hrms/hr/doctype/manpower_request/manpower_request.py
hrms/api/approval.py
hrms/api/manpower.py
hrms/hr/utils.py
hrms/tests/test_manpower_request_visibility.py
verify:   deploy (no migrate); log in as Administrator -> Manpower Request list empty, form/print refused
flags:    open by Frappe design for literal Administrator: /api/resource/... and frappe.client.get
next:     job-description attachments (WIP in ~/held-back/job-files-wip.patch), then Replacement Leave
