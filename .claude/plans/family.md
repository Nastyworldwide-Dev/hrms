CLASS: a "not approved" decision that can be saved with no reason (P0-10).
approval.decide requires one since the P0-10 fix; remote check-ins decide
through their own endpoint and still took an empty remark.

Call sites of remote_checkin._decide:
hrms/api/remote_checkin.py:reject — same-root, fixed here (reason required, trimmed).
hrms/api/remote_checkin.py:approve — not-affected: approving needs no reason (pinned by test).
frontend/src/views/RemoteApprovals.vue submitDecision — not-affected by the server rule's shape; it sent an optional remark and is replaced by the Approvals page sheet in the next commit, which requires one.
hrms/tests/probes/nadi_api_matrix.py — not-affected: probe calls with an unknown request, refused before the reason check.
