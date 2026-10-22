GOAL: a request whose first approver left or was disabled shows on the next approver's Approvals page and Home count.
DONE WHEN: _sent_to_me admits the line's first approver; backups further up still are not sent it.
CHECK: PYTHONPATH=. python3 hrms/api/test_approvals_list.py (87 OK); live probe on fresh.local: director page True, Home 1.
