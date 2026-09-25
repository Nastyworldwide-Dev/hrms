CLASS: an action that answers success while its effect did not happen

Instance: 25 Sep report — Save & rebuild answered "done" and wrote no attendance (shift auto attendance off); fixed in bca921ace.

Sites (verified by reading each):
- hrms/api/attendance_fix_days.py _apply (bulk Fix days) — same-root: checked only deadlocked/running; now the shared fd.not_applied() rule
- hrms/api/attendance_fix_day.py _finish — same-root: now the same not_applied() rule (one rule, two callers)
- frontend/src/components/CheckinDecisionSheet.vue — same-root: decisionToast computed tone "warning" for "Approved, attendance was not updated" and the sheet showed it as neutral info
- hrms/api/approval.py decide — not-affected: one submit transaction; any on_submit failure rolls the decision back
- hrms/hr/doctype/attendance_request create_attendance_records — not-affected: a holiday/leave day skipped by design, said via msgprint; a request that would create nothing is refused at filing
- hrms/api/remote_checkin.py _decide — not-affected: returns attendance_repair; the sheet now shows its tone
- hrms/api/push.py subscribe — not-affected: returns {success, message}; optional feature

Locked: test_fix_days.py (+1), decision-toast-tone.test.js (+1).
