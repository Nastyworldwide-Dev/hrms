CLASS: "what kind of day is this" is answered by the holiday calendar only; the roster's Day Type must win for every rule.
hrms/utils/ot_calculation.py:_classify_day same-root (fixed: roster first, calendar after)
hrms/hr/doctype/employee_checkin/employee_checkin.py:244 same-root (calls _classify_day)
hrms/hr/doctype/shift_type/shift_type.py:688 same-root (calls _classify_day)
hrms/hr/doctype/shift_type/shift_type.py:794 same-root (calls _classify_day)
hrms/hr/doctype/shift_type/shift_type.py:1096 same-root (calls _classify_day)
hrms/utils/approval_reminders.py:137 same-root (calls _classify_day)
hrms/utils/shift_reminders.py:193 same-root (calls _classify_day)
hrms/utils/ot_calculation.py:579,687,1018,1127 same-root (call _classify_day)
