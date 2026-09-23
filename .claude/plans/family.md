CLASS: a list or count of requests gated on ROUTING alone. approval.decide checks
read (_request_read_allowed) before routing (_is_routed_approver); routing's HR
branch admits System Manager, whom approval_row_scope denies read. Any surface
that skips the read gate shows an admin-only login every team's requests.

INSTANCE: approvals_list.get_waiting_for_me listed rows on routing alone
(review of be4b81edf).

Call sites of _is_routed_approver:
hrms/api/approvals_list.py:get_waiting_for_me — same-root, fixed here (read first).
hrms/api/needs_you.py:_pending_for — same-root, fixed here (Home's count must equal the page).
hrms/api/approval.py:_decision_access — not-affected: _request_read_allowed runs first (line 214).
hrms/utils/approved_request_guard.py:158 — not-affected: guards a WRITE on an already-loaded doc the caller is saving; it adds rights to own/routed, never lists.
hrms/mixins/pwa_notifications.py:184 — not-affected: picks recipients of a notification, discloses nothing to the caller.
hrms/hr/doctype/remote_checkin_request/remote_checkin_request.py:143 — not-affected: remote check-ins have their own company-fenced query (_pending_for_approver_query).
hrms/tests/probes/lifecycle_probe.py — not-affected: test probe.
