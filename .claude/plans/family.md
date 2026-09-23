CLASS: a cap applied before asking whose the row is (review of 474d12d34).
The site-wide oldest 50 pending of a type were read first and only then
filtered to the caller, so an approver's own newer request fell past the cap.
With the Requests Team tab cut, Approvals is the only door, so the row was lost.

Call sites and verdicts:
hrms/api/approvals_list.py get_waiting_for_me — same-root, fixed here (_mine_of pages until SCAN_CAP of MY rows; SCAN_LIMIT 1000 bounds cost, capped=true past it).
hrms/api/needs_you.py _pending_for — same-root, fixed here (reuses _mine_of, so Home counts what the page lists).
hrms/api/remote_checkin.py list_pending_for_approver — not-affected: its query filters by the caller's routing in SQL before the limit.
