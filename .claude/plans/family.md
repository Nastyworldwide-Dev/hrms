CLASS: a "not approved" decision saved with no reason (P0-10), through any door.

INSTANCE: Desk. HR User / HR Manager / System Manager may write `status` on the
Remote Checkin Request form, which never reaches remote_checkin._decide
(review of 9204e9802).

Write paths to Remote Checkin Request.status = Rejected:
hrms/hr/doctype/remote_checkin_request/remote_checkin_request.py:validate — same-root, fixed here (only when status BECOMES Rejected).
hrms/api/remote_checkin.py:_decide — not-affected: already requires a reason (9204e9802); the validate rule agrees with it.
hrms/api/attendance_fix_day.py:192/836/1295 — not-affected: reads remote_approval_status, never writes Rejected.
hrms/api/approvals_list.py — not-affected: read-only.
hrms/patches/v16_0/repair_public_selfies.py — not-affected: touches selfie files, not status.
hrms/overrides/remote_checkin_request_hooks.py:462 — not-affected: reacts to a Rejected save, does not set it.
