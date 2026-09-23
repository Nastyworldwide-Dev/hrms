CLASS: worked-day pairing bucketed by calendar day, so a shift across midnight never paired
hrms/utils/worked_days.py:punch_days same-root (pairs IN with the next OUT; reads one day past end)
hrms/api/home.py:get_home_week same-root (via paired_days)
hrms/api/calendar.py:get_month_flags same-root (via punch_days)
hrms/api/requests_summary.py:_unmarked not-affected — keys on shift_actual_start, already shift-anchored
