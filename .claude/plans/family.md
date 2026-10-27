CLASS: a daily reminder that can arrive twice or on the approver's day off
hrms/utils/approval_reminders.py send_daily_reminders same-root — _reminded_today + _off_today
hrms/utils/shift_reminders.py not-affected — dedupes per shift (_sent_this_shift) and checks _is_working_day
hrms/hooks.py comment only
