CLASS: a rounding guard sized for float fuzz when the real error is the STORAGE precision (nine decimals of an hour). One stored minute is 0.016666667 h, a hair over a whole minute, so it read "2m" rounded up; a stored third read "19m" rounded down. An unknown rounding word silently fell through to "nearest".
hrms/utils/ot_precision.py:hours_as_words same-root (fixed here: guard 1e-6 minute; an unknown rounding raises ValueError)
hrms/hr/doctype/ot_request/ot_request.py:validate_claimed_hours not-affected — passes only "up" and "down", the two valid words
hrms/utils/ot_precision.py:stored_ot_hours not-affected — compares at nine decimals with Decimal, no float guard
docs/glass/audit/2026-09-08-ot-precision-probe.py not-affected — a probe, calls no hours_as_words
