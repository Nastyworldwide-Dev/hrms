CLASS: one optional source failing a whole read (same class as 8fc7dbe6a).

Call sites and verdicts:
hrms/api/request_counts.py get_my_request_counts — same-root, fixed here (per-type try/except, logged).
hrms/api/approvals_list.py get_waiting_for_me — not-affected: already per-type try/except + _types_on_site.
hrms/api/needs_you.py get_needs_you — not-affected: already per-type try/except + table check.
