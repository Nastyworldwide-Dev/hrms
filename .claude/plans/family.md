CLASS: a "no overtime" reason that ignores approved leave on the day
hrms/utils/ot_calculation.py _explain_no_overtime same-root — reads leave_day.full_day_leave when the day has no taps
hrms/hr/doctype/ot_request/ot_request.py validate_claimed_hours same-root — calls _explain_no_overtime
hrms/utils/ot_calculation.py get_ot_claim_capacity same-root — calls _explain_no_overtime (PWA no_overtime_reason)
hrms/api/__init__.py incomplete OT days not-affected — leave days skipped by request_covered_days + _legit_zero_day
hrms/hr/doctype/ot_request/ot_request.py:271 same-root — import of the fixed function
hrms/hr/doctype/ot_request/ot_request.py:273 same-root — Save refusal now names the leave
hrms/tests/test_ot_claim_monthly_capacity.py:185 not-affected — comment in a test
