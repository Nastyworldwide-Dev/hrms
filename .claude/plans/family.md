CLASS: a fallback returned a dict with a None field that a caller does arithmetic on
hrms/utils/holiday_list.py:_record_calendar same-root — as_dict carries the calendar's from_date
hrms/utils/holiday_list.py:get_holiday_dates same-root — the only as_dict caller; add_days(to.from_date, -1) now gets a date
hrms/utils/holiday_list.py:_ended_calendar not-affected — returns a real assignment row (from_date set)
