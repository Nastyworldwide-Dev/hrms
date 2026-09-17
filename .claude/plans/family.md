# FAMILY — one employee-day rebuilt twice in a single recovery pass

CLASS: a pass that owns MORE days than it iterates. `rostered_shift` suppresses
the punch hook for every day a re-stamped tap touches (`also_rebuilding`), then
re-marks those days itself. When such a day ALSO has its own step later in the
same plan, both steps rebuild it. Two rebuilds of one employee-day race each
other, take `tabAttendance` and `tabEmployee Checkin` in opposite order, and
deadlock (1213) — the live class fixed by the lock-order work.

ROOT CAUSE: hrms/utils/attendance_recovery.py::_fix_rostered_day — the moved-to
day was added to `days` unconditionally, with no test for "a later step owns
this day". Fixed there, once: the step skips a day the pass has not reached yet
(`pending`), so the day is re-marked exactly once, by the step that owns it.
A day with no step of its own is still re-marked here — its hook is silenced.

## _fix_rostered_day — the defective step

hrms/utils/attendance_recovery.py:1278 — same-root (fixed here)
  The only production caller, inside `_apply_rostered_shift`. It now computes
  the not-yet-reached days of its own plan and passes them as `pending`.
hrms/utils/attendance_recovery.py:2661 — same-root (fixed here)
  `AUTO_STEPS["rostered_shift"] = _apply_rostered_shift`, the entry point the
  nightly job and `run_endgame` use. Fixed by the same change; no edit needed.
hrms/tests/test_rostered_shift_step.py:285 — not-affected — test seam
  Calls `_apply_rostered_shift` directly, which supplies `pending` itself.
  `pending` defaults to `frozenset()`, so any other direct caller keeps the old
  behaviour (re-mark every touched day) rather than silently skipping one.

## also_rebuilding / remark_day_after_commit — NOT the same class

`also_rebuilding` widens the suppression set; that is correct and unchanged —
the hook must not queue a second rebuild while the pass holds the day. The
defect was the pass failing to divide the work it had taken, not the taking.
Verified: hrms/utils/day_remark.py:87 and :98 are untouched, and the day_remark
and day_remark_hooks suites are green.

---

# FAMILY — "Selfie failed / frappe.exceptions.PermissionError" on a punch

CLASS: a PWA screen asking frappe's generic `upload_file` to create a PUBLIC
File as the signed-in employee. A site with System Settings ->
only_allow_system_managers_to_upload_public_files on refuses that for every
user below System Manager, and frappe's friendly guard around it
(frappe/core/doctype/file/file.py:205, `except PermissionError`) catches the
BUILTIN PermissionError, not frappe.exceptions.PermissionError — which is a
plain Exception subclass. The refusal therefore escapes with no message at
all, so the phone can only show the class name.

ROOT CAUSE: our side asked for a public file at all. Staff hold no create
rights of their own on File (or Employee Checkin) on a hardened site; every
other staff write in this app already goes through an hrms.api endpoint.

REPRODUCED: bench fresh.local, 17 Sep 2026, staff user (Employee +
Employee Self Service), setting on, public File insert ->
frappe.exceptions.PermissionError. Same insert private, or setting off -> OK.

## Callers that create a File from the PWA

frontend/src/components/CheckInPanel.vue:1265 — same-root (fixed here)
  The reported symptom. Now posts the frame to
  hrms.api.remote_checkin.upload_selfie, which stores it for the caller.
frontend/src/views/sop/SopFormSheet.vue:324 — not-affected
  Uploads with is_private=1. enforce_public_file_restrictions only guards
  public files, so the broken `except` is never reached.
hrms/api/__init__.py:1814 (upload_base64_file) — not-affected
  Inserts with "is_private": 1, same reason. Used by the expense and SOP
  attachment paths.
hrms/api/sop.py:68,190,271 — not-affected
  Reads and deletes File rows; creates none.

## Machine-listed sites (the scan matched the bare word `name`, not a caller)

`upload_selfie` is new in this commit and nothing calls it yet but the PWA's
uploadSelfie(); `resolve_punch_type` is untouched. The eight rows below are
prose in docstrings and comments containing the word "name", each verdicted:

hrms/hooks.py:340 — not-affected — a comment about Employee autonaming.
hrms/hr/doctype/appraisal/import_kra_kpi.py:114 — not-affected — accepts an
  EXISTING File doc name; creates no File.
hrms/hr/doctype/appraisal/import_kra_kpi.py:37 — not-affected — the same
  docstring line.
hrms/hr/report/checkin_provenance_audit/checkin_provenance_audit.py:6 — not-affected — prose about colliding checkin autonames.
hrms/overrides/employee_hrms_scope.py:143 — not-affected — prose about filing
  a request in one's own name.
hrms/patches/v16_0/add_forgotten_checkouts_link.py:18 — not-affected — prose
  about linking a Report by name.
hrms/sync/account_shells.py:385 — not-affected — prose about ledger names.
hrms/sync/checkin_recovery.py:7 — not-affected — prose about the source's name.
