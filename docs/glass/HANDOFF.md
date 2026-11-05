# HANDOFF
prompt:   HR as second approver on expense claims; calendar day sheet; IC number (owner, 3-5 Nov 2026)
status:   done
commit:   alpha.82 on nz-glass (043c9b769, d0737d57e, 08b4dd8c8, 64a7143bb)
files:    hrms/utils/claim_stages.py
hrms/api/approval.py
hrms/api/approvals_list.py
hrms/hr/doctype/expense_claim/expense_claim.py
hrms/utils/employee_ic.py
hrms/api/calendar.py
verify:   deploy WITH migrate; staff claim -> manager Approve -> "Waiting for HR" -> HR Approve -> paid
flags:    bench (database) suites not run here; HR's early decision is final, as before
next:     boss calendar ideas (mockup-calendar-boss-ideas.html) wait on a pick
