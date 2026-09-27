CLASS: a new document inherits a deleted one's links through a re-used name (revert_series_if_last)
hrms/api/__init__.py withdraw_request — same-root (live links still refuse; cancelled rows of a re-used name no longer do; dynamic-link check kept)
hrms/api/request_history.py — same-root, fixed earlier this release (history older than the document excluded)
hrms/api/approval.py get_rejection_reason — not-affected — reads Comments by name; a re-used name's old reason could show; ticket: filter by creation >= doc.creation
frontend/e2e/pendingRequest.mjs — not-affected — the fixture that surfaced it; now withdraws cleanly
