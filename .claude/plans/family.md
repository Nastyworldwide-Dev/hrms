CLASS: a per-day lookup inside a per-employee loop in a report
hrms/hr/report/rest_day_differences/rest_day_differences.py:_rows same-root — calendar resolved once per span, not per day
hrms/hr/report/rest_day_differences/rest_day_differences.py:_columns same-root — "Which dates" x2 renamed
hrms/hr/report/rest_day_differences/rest_day_differences.py:mine same-root — the cached resolver
hrms/hr/report/announcement_confirmations/announcement_confirmations.py:24 not-affected — its own private _columns, same name, no call into this report
hrms/hr/report/announcement_confirmations/announcement_confirmations.py:76 not-affected — its own private _columns
hrms/hr/report/attendance_day_audit/attendance_day_audit.py:60 not-affected — its own private _columns
hrms/hr/report/attendance_ownership_check/attendance_ownership_check.py:51 not-affected — its own private _rows, no per-day calendar resolver
hrms/hr/report/attendance_ownership_check/attendance_ownership_check.py:52 not-affected — its own private _columns
hrms/hr/report/checkin_provenance_audit/checkin_provenance_audit.py:40 not-affected — its own private _rows
hrms/hr/report/checkin_provenance_audit/checkin_provenance_audit.py:51 not-affected — its own private _columns
hrms/hr/report/missed_checkouts_after_midnight/missed_checkouts_after_midnight.py:39 not-affected — its own private _columns/_rows
hrms/hr/report/out_of_radius_activity/out_of_radius_activity.py:44 not-affected — its own private _columns
hrms/hr/report/request_access_health/request_access_health.py:34 not-affected — its own private _columns
hrms/hr/report/roster_patterns/roster_patterns.py:41 not-affected — its own private _rows; no calendar resolver per day
hrms/hr/report/roster_patterns/roster_patterns.py:42 not-affected — its own private _columns
hrms/hr/report/staff_without_a_shift/staff_without_a_shift.py:71 not-affected — its own private _columns
hrms/hr/report/unclaimable_days/unclaimable_days.py:41 not-affected — its own private _rows
hrms/hr/report/unclaimable_days/unclaimable_days.py:42 not-affected — its own private _columns
hrms/tests/_qb_stub.py:261 not-affected — a test stub's own _rows method
