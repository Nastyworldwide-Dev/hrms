CLASS: rest-day/holiday overtime claimed and paid exact to the second instead of in HR's 30-minute bands
hrms/utils/ot_calculation.py:928 same-root — claim capacity (form, discovery, save cap) bands the holiday part
hrms/utils/ot_calculation.py:689 not-affected — the worked record keeps every minute; only claims and pay are banded
hrms/utils/ot_calculation.py:705 not-affected — get_ot_pay prices approved claimed_hours, which are now banded at filing
hrms/api/__init__.py:795 not-affected — discovery reads uncapped_hours from the same capacity
hrms/hr/doctype/ot_request/ot_request.py:156 not-affected — the save cap is the same capacity
hrms/utils/attendance_recovery.py:3044 not-affected — compares claimed hours to priced hours of the same engine
