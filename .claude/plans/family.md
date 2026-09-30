CLASS: a range split at the second calendar's start date assumed that start lay inside the range
hrms/utils/holiday_list.py:get_holiday_dates_between_range same-root — split clamped with max(from_date, start_date); first part skipped when empty
hrms/utils/holiday_list.py:get_holiday_dates_between not-affected — takes the range it is given
