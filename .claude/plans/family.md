CLASS: a new rule that only governs new work, leaving the old rows in the old shape, so two figures for one thing live side by side (a 1.37 claim filed yesterday beside a 1.0 claim filed today). Owner ruled 5 Oct 2026: cut the open claims filed before the half-hour rule too.
hrms/patches/v16_0/band_open_ot_claims_to_half_hours.py same-root (new: one-time cut of docstatus 0, Overtime Pay, not Rejected claims, logged old and new, modified untouched, idempotent)
hrms/patches.txt same-root (new line under post_model_sync, so it runs on deploy with no console step)
hrms/hr/doctype/ot_request/ot_request.py:band_typed_claim not-affected — the rule for NEW and EDITED claims, unchanged
hrms/hr/doctype/ot_request/ot_request.py:decided claims not-affected — a submitted claim is never touched: an approver read that figure and it may be priced
hrms/hr/doctype/replacement_leave_claim not-affected — raw hours convert to days; the patch filters to Overtime Pay
