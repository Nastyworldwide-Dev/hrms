CLASS: a submitted request whose decision field still holds its waiting word rendered as waiting

Instance: owner report 25 Sep 2026: "2 fix a day still Open" (On Duty 27 Jun, 29 Jul) — listed under Approved, chip "Open".

Sites:
- frontend/src/utils/requestStatus.js requestStatus — same-root (the one status rule every chip, filter and sheet reads)
- hrms/api/request_counts.py _bucket — not-affected: already counts docstatus 1 non-Rejected as approved
- hrms/api/approvals_list.py — not-affected: lists only docstatus 0, so these never reach the approver (correct: nothing to decide)
- hrms/patches/v16_0/backfill_request_decision_status.py — not-affected: fills only NULL; the stored "Open" on these rows is historical data, left as is (repair needs the owner's word)

Locked: src/utils/__tests__/requestStatus.test.js (+1).
