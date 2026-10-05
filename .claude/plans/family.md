CLASS: a lookup built into a dict keyed by person, fed by a query with no order, so when two rows exist for one person the one that wins is whichever the database listed last. HR's half day (a submitted Attendance) could lose to an older draft row saying Present.
hrms/api/team.py:member_statuses same-root (fixed here: order_by docstatus asc, modified asc, so the submitted and latest row is the one the dict keeps)
hrms/api/team.py:leaves dict not-affected — filtered to docstatus 1 and status Approved, one row per person per day by the overlap rule
hrms/api/calendar.py:get_day not-affected — reads rows from member_statuses
hrms/api/calendar.py:month view not-affected — reads Attendance directly per day, not through a person-keyed dict
hrms/utils/team_status.py:derive_member_status not-affected — takes the status it is given
