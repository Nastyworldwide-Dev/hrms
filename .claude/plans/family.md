CLASS: a feature reading approved leave its own way, or not at all
hrms/api/home.py get_home_week same-root — rest days and holidays inside a leave are not days on leave
hrms/api/calendar.py _leave_days not-affected — the grid draws the holiday/weekly-off mark on those days anyway
hrms/utils/leave_cover.py not-affected — counts any leave day as covered on purpose (Fix day rebuild guard)
