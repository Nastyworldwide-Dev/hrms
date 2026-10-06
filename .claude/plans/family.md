CLASS: an approved request cancelled with nobody told (owner ruling R3, 6 Oct): balances and attendance reversed silently; the approver and HR found out by accident.
hrms/utils/cancel_notice.py same-root (notify_cancelled: designated approvers + HR in the company fence, not the canceller, not the employee; only when it WAS approved; never blocks the cancel)
hrms/hooks.py same-root (on_cancel on the 7 DECIDE_THEN_SUBMIT doctypes, merged with existing entries)
hrms/api/approvals_list.py:request_when same-root (one rule for "which days is this request about"; the list and the notice share it)
hrms/utils/approved_request_guard.py not-affected — decides WHO may cancel; unchanged
hrms/*/on_cancel reversals not-affected — balances and attendance still reverse in each doctype as before
