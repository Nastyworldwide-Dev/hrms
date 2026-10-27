CLASS: one leave row per person per day assumed; an AM + PM pair or a multi-day half day misread
hrms/utils/shift_reminders.py _apply_leave/_half_on same-root — all rows kept, AM+PM = full day, multi-day without a date not guessed
hrms/utils/approval_reminders.py _away_approvers not-affected — a half day there means "not away"; two halves is a ticket candidate, rare
