CLASS: a per-row permission question asked once per row instead of once per list (alpha.35 O1 fixed the leave list; the approvals list still asked per row).
hrms/api/approvals_list.py:get_waiting_for_me same-root (one may_read_leave_reasons call per page's leave list, answers zipped strict)
hrms/api/approvals_list.py:_row same-root (takes the answer; None still asks the single form, for its other callers)
hrms/api/__init__.py:get_leave_applications not-affected — already batched in alpha.35
hrms/api/approval.py:may_read_leave_reason not-affected — the single form is the batch with one row
