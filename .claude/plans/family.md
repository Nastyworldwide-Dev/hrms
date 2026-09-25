CLASS: a submitted request whose decision field still holds its waiting word read as waiting (server side)

Instance: Calendar day sheet — "Claim waiting" on overtime approved before the decision field existed (status Open, docstatus 1).

Sites:
- hrms/api/calendar.py _day_claim — same-root (a submitted Open claim is sent as Approved)
- hrms/api/__init__.py get_claimable_ot_summary claimed_days — not-affected: sends docstatus; the PWA labels it through requestStatusChip (62246a4af)
- hrms/api/__init__.py get_filters history — not-affected: filters status in (Approved, Rejected), so a submitted Open row is simply not in the approver's history (no wrong label shown); noted
- hrms/api/approvals_list.py — not-affected: docstatus 0 only
- hrms/api/request_counts.py — not-affected: docstatus 1 non-Rejected = approved

Locked: hrms/api/test_calendar_day_claim.py (+2).
