CLASS: a per-row permission question asked once per row instead of once per person. get_leave_applications asked may_read_leave_reason for every row: one Employee company read per row for HR, one routing check per row for an approver, so a 50-row list made 50+ database reads for answers that depend only on the person and the request's named approver.
hrms/api/approval.py:may_read_leave_reasons same-root (new: the batch form: own employees and HR sight once, ONE get_all for the companies of the people listed, routing once per (employee, leave_approver))
hrms/api/approval.py:may_read_leave_reason same-root (now the batch with one row, so the single and batch forms cannot drift)
hrms/api/__init__.py:get_leave_applications same-root (uses the batch)
hrms/api/approvals_list.py not-affected — asks for the rows routed to the caller, already filtered; calls the single form per row of a short list (ticket: switch to the batch if the approvals list grows)
