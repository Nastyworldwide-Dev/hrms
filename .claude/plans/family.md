CLASS: a pay rule enforced on the PREVIEW (the punch cap is banded to half hours) but not on what the person TYPES, so the stored claim can be a figure that is no pay step (1.37) and every screen then shows a different number for the same claim (OD2 of the OT decimals hunt, owner ruling 5 Oct 2026: round typed Overtime Pay claims down to the half hour).
hrms/hr/doctype/ot_request/ot_request.py:band_typed_claim same-root (new: cuts a new or edited Overtime Pay claim to the half hour below, called in validate before the cap check)
hrms/utils/ot_precision.py:half_hour_claim same-root (new: Decimal, so a typed 1.5 stays 1.5)
hrms/hr/doctype/ot_request/ot_request.py:validate_claimed_hours not-affected — still compares at nine decimals; a banded claim can only be at or below the cap
hrms/hr/doctype/replacement_leave_claim/replacement_leave_claim.py not-affected — Replacement Leave converts raw hours to days; band_typed_claim returns early for it
hrms/hr/doctype/ot_request/ot_request.py:on_submit/approval not-affected — an unchanged saved claim is never re-banded (an approver's decision is on the figure they read)
frontend/src/views/ot/OTRequestForm.vue ticket ticket-ot-request-py-refactor — the form does not yet tell the person their typed figure will be cut to the half hour; the saved list shows the banded figure
