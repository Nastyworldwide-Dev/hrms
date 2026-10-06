CLASS: a request held by an approver who is away (owner ruling R2, 6 Oct): the backup was asked only after the normal 3 working days, however long the first approver was on leave.
hrms/utils/approval_reminders.py:plan_reminders same-root (away first approver -> backup asked after 2 working days, both told)
hrms/utils/approval_reminders.py:_waiting_requests same-root (first_away from ONE Leave Application read per run)
hrms/api/approval.py:decide not-affected — the backup may already decide (alpha.20 line rule); this only asks them sooner
hrms/hr/utils.py:get_designated_approvers not-affected — the line itself is unchanged
