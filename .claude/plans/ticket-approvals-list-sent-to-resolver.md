# Ticket: one "who is this request sent to" resolver

Hotspot: hrms/api/approvals_list.py, 7 fixes in 90 days (latest b44df6e87, 22 Oct 2026).

Problem: "sent to me" (approvals_list._sent_to_me) and "who it is routed to"
(hr.utils.validate_staff_approver -> chain[0], approval_reminders "first",
remote_checkin_request_hooks.resolve_approver) are separate rules. They drifted:
a request whose approver had Left was routed onward but sent to nobody.

Change: one helper in hrms/hr/utils.py, e.g. first_approver(employee, doctype),
that every one of those reads. _sent_to_me keeps its stored-field check (a
request already stamped to someone) and asks the helper for the rest.

Also: the walk now runs for every row the cheap checks miss (review warning).
Only matters if Home or Approvals is reported slow.

Status: open, not started. Needs Nabil's go-ahead.
