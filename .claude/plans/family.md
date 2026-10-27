CLASS: a person-facing reminder that knows the shift and the rest day but not the approved leave
hrms/utils/shift_reminders.py send_due_reminders same-root — _apply_leave drops full-day leave, half day moves to mid-shift
hrms/utils/approval_reminders.py _away_approvers not-affected — already reads approved leave (skips away approvers)
hrms/utils/announcement push / attendance health not-affected — not tied to a shift day
