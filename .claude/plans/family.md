CLASS: a whitelisted write that accepts GET, so any page can trigger it without a CSRF token (same class as f38f46320, hrms/api)
hrms/hr/doctype/employee_attendance_tool/employee_attendance_tool.py:170 same-root — POST only
hrms/hr/doctype/employee_checkin/employee_checkin.py:394 same-root — POST only
hrms/hr/doctype/employee_referral/employee_referral.py:50 same-root — POST only
hrms/hr/doctype/exit_interview/exit_interview.py:64 same-root — POST only
hrms/hr/doctype/goal/goal.py:202 same-root — POST only
hrms/hr/doctype/goal/goal.py:212 same-root — POST only
hrms/hr/doctype/goal/goal.py:230 same-root — POST only
hrms/hr/doctype/interview/interview.py:224 same-root — POST only
hrms/hr/doctype/interview/interview.py:352 same-root — POST only
hrms/hr/doctype/job_applicant/job_applicant.py:111 same-root — POST only
hrms/hr/doctype/job_applicant/job_applicant.py:160 same-root — POST only
hrms/hr/doctype/leave_ledger_entry/leave_ledger_entry.py:211 same-root — POST only
hrms/hr/doctype/leave_policy_assignment/leave_policy_assignment.py:485 same-root — POST only
hrms/hr/doctype/leave_policy_assignment/leave_policy_assignment.py:515 same-root — POST only
hrms/overrides/employee_payment_entry.py:325 same-root — POST only
hrms/hr/doctype/employee_checkin/employee_checkin.py:323 not-affected — biometric device ingestion, token auth, devices may GET; gated by create permission; named exception in the test
