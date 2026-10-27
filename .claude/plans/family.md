CLASS: a person-facing state built from the shift alone, ignoring approved leave
hrms/api/now.py _state/get_now same-root — "leave" state from leave_day.full_day_leave
frontend/src/components/NowBar.vue + CheckInPanel.vue same-root — leave line + colour, no Check in button
hrms/utils/checkin_sweeper.py ticket .claude/plans/ticket-intelligence-gaps.md — tags abandoned INs without reading leave
frontend/src/components/HomeWeek.vue ticket .claude/plans/ticket-intelligence-gaps.md — week line counts leave as not worked
hrms/api/approval.py:460 not-affected — a different local _state(doc) (the request's decision state), not now.py's
hrms/api/approval.py:500 not-affected — same local _state(doc) in approval.py
hrms/api/approval.py:1102 not-affected — same local _state(doc) in approval.py
hrms/api/approval.py:1127 not-affected — same local _state(doc) in approval.py
hrms/tests/probes/leave_by_probe.py:29 not-affected — a bench probe that prints get_now(); the new state key only adds a case
