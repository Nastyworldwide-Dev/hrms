CLASS: a decision's WHY recorded in one place and never carried to the one it concerns. decide() forces an approver to write a reason for a rejection and kept it only as a Comment (read by the request sheet); the employee's PWA notification, built inside on_submit, said only 'Rejected by X on date', so the employee was told no and never why (flows hunt M1, 5 Oct 2026, proven end to end on fresh.local). Fixed where the two meet: decide() sets doc.flags.rejection_reason BEFORE doc.submit() and notify_approval_status appends it (HTML-escaped, Rejected only). Every request type routes through that one mixin method, so all seven types carry the reason.
hrms/api/__init__.py:1021 not-affected — a comment or docstring that names decide(); the line itself does not build or send a decision notification
hrms/api/needs_you.py:13 not-affected — a comment or docstring that names decide(); the line itself does not build or send a decision notification
hrms/hr/doctype/attendance_request/attendance_request.py:50 not-affected — a comment or docstring that names decide(); the line itself does not build or send a decision notification
hrms/hr/doctype/remote_checkin_request/remote_checkin_request.py:116 ticket .claude/plans/ticket-remote-checkin-refactor.md — a comment about WHO may decide; a Remote Checkin Request is decided through hrms.api.remote_checkin.approve/reject, not decide(), and does not use PWANotificationsMixin: its rejection reason is a separate path (the check-in's own reject_says_why, test_remote_checkin_reject_says_why.py)
hrms/hr/utils.py:1402 not-affected — a comment or docstring that names decide(); the line itself does not build or send a decision notification
hrms/overrides/approval_row_scope.py:18 not-affected — a comment or docstring that names decide(); the line itself does not build or send a decision notification
hrms/overrides/approval_row_scope.py:64 not-affected — a comment or docstring that names decide(); the line itself does not build or send a decision notification
hrms/overrides/ot_row_scope.py:12 not-affected — a comment or docstring that names decide(); the line itself does not build or send a decision notification
hrms/patches/v16_0/approver_reads_past_employee_user_permissions.py:14 not-affected — a comment or docstring that names decide(); the line itself does not build or send a decision notification
hrms/public/js/utils/request_approval.js:139 not-affected — the Desk button that calls hrms.api.approval.decide; it already requires a reason for a rejection (P0-10) and goes through decide(), so the notice gets it
hrms/public/js/utils/request_approval.js:143 not-affected — the Desk button that calls hrms.api.approval.decide; it already requires a reason for a rejection (P0-10) and goes through decide(), so the notice gets it
hrms/public/js/utils/request_approval.js:147 not-affected — the Desk button that calls hrms.api.approval.decide; it already requires a reason for a rejection (P0-10) and goes through decide(), so the notice gets it
hrms/tests/probes/lifecycle_probe.py:546 not-affected — a probe script's own text mentioning decide(); it sends no notification and reads none
hrms/tests/probes/lifecycle_probe.py:551 not-affected — a probe script's own text mentioning decide(); it sends no notification and reads none
hrms/tests/probes/lifecycle_probe.py:560 not-affected — a probe script's own text mentioning decide(); it sends no notification and reads none
hrms/tests/probes/lifecycle_probe.py:570 not-affected — a probe script's own text mentioning decide(); it sends no notification and reads none
hrms/tests/probes/lifecycle_probe.py:575 not-affected — a probe script's own text mentioning decide(); it sends no notification and reads none
hrms/tests/probes/lifecycle_probe.py:595 not-affected — a probe script's own text mentioning decide(); it sends no notification and reads none
hrms/tests/probes/lifecycle_probe.py:606 not-affected — a probe script's own text mentioning decide(); it sends no notification and reads none
hrms/tests/probes/lifecycle_probe.py:624 not-affected — a probe script's own text mentioning decide(); it sends no notification and reads none
hrms/tests/probes/lifecycle_probe.py:646 not-affected — a probe script's own text mentioning decide(); it sends no notification and reads none
hrms/tests/probes/lifecycle_probe.py:658 not-affected — a probe script's own text mentioning decide(); it sends no notification and reads none
hrms/tests/probes/lifecycle_probe.py:689 not-affected — a probe script's own text mentioning decide(); it sends no notification and reads none
hrms/tests/probes/lifecycle_probe.py:695 not-affected — a probe script's own text mentioning decide(); it sends no notification and reads none
hrms/tests/probes/lifecycle_probe.py:709 not-affected — a probe script's own text mentioning decide(); it sends no notification and reads none
hrms/tests/probes/lifecycle_probe.py:714 not-affected — a probe script's own text mentioning decide(); it sends no notification and reads none
hrms/tests/probes/lifecycle_probe.py:743 not-affected — a probe script's own text mentioning decide(); it sends no notification and reads none
hrms/tests/probes/lifecycle_probe.py:748 not-affected — a probe script's own text mentioning decide(); it sends no notification and reads none
hrms/tests/probes/lifecycle_probe.py:757 not-affected — a probe script's own text mentioning decide(); it sends no notification and reads none
hrms/tests/probes/lifecycle_probe.py:762 not-affected — a probe script's own text mentioning decide(); it sends no notification and reads none
hrms/tests/probes/lifecycle_probe.py:770 not-affected — a probe script's own text mentioning decide(); it sends no notification and reads none
hrms/tests/probes/lifecycle_probe.py:776 not-affected — a probe script's own text mentioning decide(); it sends no notification and reads none
hrms/tests/probes/lifecycle_probe.py:785 not-affected — a probe script's own text mentioning decide(); it sends no notification and reads none
hrms/tests/probes/lifecycle_probe.py:805 not-affected — a probe script's own text mentioning decide(); it sends no notification and reads none
hrms/tests/probes/lifecycle_probe.py:818 not-affected — a probe script's own text mentioning decide(); it sends no notification and reads none
hrms/tests/probes/lifecycle_probe.py:839 not-affected — a probe script's own text mentioning decide(); it sends no notification and reads none
hrms/mixins/pwa_notifications.py:notify_approval_status same-root (fixed here: carries the reason for a Rejected decision)
hrms/api/approval.py:decide same-root (fixed here: hands the reason to the document before submit)
hrms/hr/doctype/leave_application/leave_application.py:on_submit not-affected — calls the mixin; gets the reason through it (proven on a real Leave Application)
hrms/hr/doctype/expense_claim/expense_claim.py:on_submit not-affected — calls the same mixin method; same fix applies
hrms/hr/doctype/shift_request/shift_request.py:on_submit not-affected — same mixin method
hrms/hr/doctype/ot_request/ot_request.py:on_submit not-affected — same mixin method (test_request_outcome_visible.py)
hrms/hr/doctype/attendance_request/attendance_request.py:on_submit not-affected — same mixin method
hrms/hr/doctype/replacement_leave_claim/replacement_leave_claim.py:on_submit not-affected — same mixin method
hrms/hr/doctype/compensatory_leave_request/compensatory_leave_request.py:on_submit not-affected — same mixin method
