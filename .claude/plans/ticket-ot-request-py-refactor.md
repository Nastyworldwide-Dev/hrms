# Ticket: hrms/hr/doctype/ot_request/ot_request.py keeps needing fixes (hotspot, 16 fixes/90d)

WHY: validation, pricing, day-type, notification and payment state all live in one controller. Each fix (claim cap,
banding, rate label, refusal wording, precision) has landed inside validate_claimed_hours or its neighbours.

DO: split validate() into small named checks (claim vs cap, day type and rate, status guard), one test each, before the
next change to this file. Keep hours_as_words (hrms/utils/ot_precision.py) as the one place hours become words.

ALSO (same class, not yet fixed): replacement_leave_claim.py:86 prints raw {1} hours; attendance_fix_days.py request_kept
and _result print raw hours to HR (OD7); the app's capAsTime floors while lists round (OD3) and the sent-request sheet shows
decimals (OD4). OD2 (a typed claim is never banded to 30 min) changes pay: needs Nabil's ruling.

DONE 5 Oct 2026 (OD2, owner ruling): a typed Overtime Pay claim is cut DOWN to the half hour on file and on edit
(ot_request.py band_typed_claim, ot_precision.half_hour_claim); a saved claim is not re-banded when an approver decides.
LEFT: the PWA claim form should say so as the person types ("Paid in half hours: 1.37 becomes 1.0"), or the cut looks like a bug.

LIMITS OF THE HALF-HOUR RULE (review of 66f0ed539, 5 Oct 2026):
- A draft filed BEFORE the rule at 1.37 and approved with no edit stays 1.37 and is paid at 1.37: deliberate ("never changed under
  an approver"). If the owner wants them cut, a guarded patch that bands open drafts (docstatus 0, Overtime Pay) before approval.
- A cap that is not a half step (monthly allowance remaining 1.25) cuts a claim of 1.25 to 1.0; the refusal wording says "half hours".
- The sync runner skips validate, but OT Request is NOT a mirrored transaction (hrms/sync/write_block.py): checked, not affected.
