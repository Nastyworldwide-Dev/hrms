CLASS: one bad item in a scheduler loop rolled back the whole tick.

Call sites: shift_reminders.send_due_reminders — same-root, fixed (per-item commit, logged skip). _is_working_day — not-affected (already try/except per candidate). Other cron job checkin_sweeper — not-affected (not touched in this range).
