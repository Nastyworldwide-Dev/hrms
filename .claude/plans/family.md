CLASS: a person-facing sentence built from a stored float with no formatting, so the nine decimals the database keeps ("8.876944444") reach the screen. The refusal "Cannot claim ... at most 8.876944444 hours" named raw hours; the lists and the approver's screen already say "8h 52m".
hrms/hr/doctype/ot_request/ot_request.py:validate_claimed_hours same-root (fixed here: both figures go through hours_as_words; the cap rounds DOWN, the claim to the nearest minute)
hrms/utils/ot_precision.py:hours_as_words same-root (new: the one server-side "8h 52m" helper, same shape as the app's hoursAsTime)
hrms/api/attendance_fix_days.py:361,380 ticket ot-decimals — "OT Request X 8.876944444 h" in HR's Fix Day screen and log (OD7, Low), next commit
hrms/hr/doctype/replacement_leave_claim/replacement_leave_claim.py:86 ticket ot-decimals — "Cannot claim {0} day(s) ({1} hours)" prints hours unformatted, same class
hrms/mixins/pwa_notifications.py:notify_* not-affected — no OT hours in any notice sentence (hunt checked)
hrms/hr/doctype/ot_request/ot_request.py:validate_claimed_hours comparison not-affected — still compares at nine decimals (stored_ot_hours); only the TEXT changed
