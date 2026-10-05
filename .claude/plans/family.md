CLASS: a lookup that returns the stored field and nothing else, so an empty field means nobody. `_get_doc_approver` returned the approver field for Leave Application, Expense Claim and Shift Request and stopped there: a request filed by an employee whose record names no approver (21 of the 22 active employees on the test site) notified no one and sat Open. The three other request types already fell back to the employee's line, then HR (`_get_ot_approver`). Proven on fresh.local with the site's real manager account: before, nobody was told; after, the manager is. Fixed at the one resolver every notice goes through.
hrms/mixins/pwa_notifications.py:_get_doc_approver same-root (fixed here: a named approver still wins; with none named it asks `_get_ot_approver`)
hrms/mixins/pwa_notifications.py:notify_approver not-affected — the caller; it already returns quietly when the resolver finds nobody, and now finds somebody
hrms/hr/doctype/leave_application/leave_application.py:notify_leave_approver not-affected — the EMAIL path reads `self.leave_approver` directly; with none named it sends no email (ticket below: the email, unlike the PWA notice, is not routed up the line)
hrms/hr/doctype/expense_claim/expense_claim.py:after_insert not-affected — calls notify_approver (the fixed resolver)
hrms/hr/doctype/shift_request/shift_request.py:after_insert not-affected — calls notify_approver (the fixed resolver)
hrms/hr/doctype/ot_request/ot_request.py:after_insert not-affected — already routed through _get_ot_approver
hrms/hr/doctype/attendance_request/attendance_request.py:after_insert not-affected — already routed through _get_ot_approver
hrms/hr/doctype/replacement_leave_claim/replacement_leave_claim.py:after_insert not-affected — already routed through _get_ot_approver
hrms/hr/doctype/compensatory_leave_request/compensatory_leave_request.py:after_insert not-affected — has its own resolver (_get_leave_approver_or_manager): the leave approver, else the manager
hrms/api/approval_reminders.py:none not-affected — the morning reminder reads the approvals list (routing-based), not this resolver
