CLASS: a submitted request whose decision field still holds its waiting word, judged by the word

Instance: the approver's "already answered" history filtered status in (Approved, Rejected), so a request submitted before the decision field existed ("Open", docstatus 1) was missing from it.

Sites:
- hrms/api/__init__.py get_filters history — same-root (decided = docstatus 1; Expense Claim keeps approval_status because an approved expense can stay a draft until finance submits)
- other sites of the family — see docs/glass/audit/2026-09-25-defect-families.md (62246a4af, 9e71d0f9c)

Locked: hrms/tests/test_requests_history_api.py (updated; red on the old code: 2 fail).
